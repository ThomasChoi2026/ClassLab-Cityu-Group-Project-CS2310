"""HTTP/Unix transport tests with a mock Judge. No student code is executed."""
import concurrent.futures
import contextlib
import http.server
import json
import socketserver
import tempfile
import threading
import unittest
from pathlib import Path

from workflow import request, server


class MockServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    def __init__(self, path):
        self.started = threading.Event()
        self.release = threading.Event()
        super().__init__(str(path), Handler)


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, payload):
        data = json.dumps({"version": 1, **payload}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        assert self.path == "/health"
        self.reply({"status": "ready"})

    def do_POST(self):
        assert self.path == "/evaluate"
        packet = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert set(packet) == {"version", "code", "inputs", "mode"}
        assert packet["version"] == 1
        code = packet["code"]
        if code == "HOLD":
            self.server.started.set()
            assert self.server.release.wait(5)
        if code == "COMPILER_FAILURE":
            self.reply({"status": "compilation_error",
                        "diagnostic": "main.cpp:2: error: expected ';' before 'return'"})
            return
        if code == "INVALID":
            self.reply({"status": "success", "cases": [{"status": "success", "stdoutHex": "x"}]})
            return
        if code == "JUDGE_FAILURE":
            self.reply({"status": "judge_error"})
            return
        cases = []
        for line in packet["inputs"]:
            a, b = map(int, line.split())
            output = a - b if code == "WRONG" else a + b
            case = {"status": "success", "stdoutHex": f"{output}\r\n".encode().hex(), "exitCode": 0}
            if packet["mode"] == "run":
                case["stderr"] = "mock stderr"
            cases.append(case)
        self.reply({"status": "success", "cases": cases})


@contextlib.contextmanager
def mock(path):
    with MockServer(path) as worker:
        thread = threading.Thread(target=worker.serve_forever, daemon=True)
        thread.start()
        try:
            yield worker
        finally:
            worker.release.set()
            worker.shutdown()
            thread.join()
    path.unlink()


class JudgeProtocol(unittest.TestCase):
    def test_mock_full_flow(self):
        with tempfile.TemporaryDirectory() as directory:
            socket = Path(directory) / "judge.sock"
            data = Path(directory) / "state.json"
            with server(data, socket) as base:
                _, room = request(base, "/api/rooms", {"name": "Judge"})
                root = "/api/rooms/" + room["id"]
                teacher = {"X-Teacher-Key": room["teacherKey"]}
                task = {"title": "Sum", "description": "Add two integers", "starterCode": "",
                        "testCases": [
                            {"name": "Basic", "input": "2 3", "expectedOutput": "5", "visibility": "public"},
                            {"name": "HIDDEN_NAME", "input": "3 0", "expectedOutput": "3", "visibility": "hidden"}]}
                _, task = request(base, root + "/tasks", task, **teacher)
                students = []
                for name in ("Correct", "Syntax", "Wrong"):
                    _, student = request(base, root + "/students", {"name": name})
                    students.append({"X-Student-Key": student["studentKey"]})
                a, b, c = students

                def submit(code, student, attempt):
                    return request(base, root + "/submissions",
                                   {"taskId": task["id"], "code": code, "requestId": attempt,
                                    "judgement": {"status": "accepted"}}, **student)

                def run():
                    return request(base, root + "/run", {"taskId": task["id"], "code": "CORRECT", "input": "5 3"}, **a)

                self.assertEqual(run()[0], 503)
                with mock(socket) as worker:
                    status, result = run()
                    self.assertEqual((status, result["stdout"], result["stderr"], result["exitCode"]),
                                     (200, "8\r\n", "mock stderr", 0))
                    self.assertEqual(request(base, root + "/progress", **teacher)[1]["attempts"], 0)
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        first = pool.submit(submit, "HOLD", a, "a1")
                        self.assertTrue(worker.started.wait(2))
                        self.assertEqual(request(base, root + "/progress", **teacher)[1]["pending"], 1)
                        self.assertEqual(submit("CORRECT", b, "b1")[0], 429)
                        self.assertEqual(submit("HOLD", a, "a1")[1]["judgement"], "pending")
                        worker.release.set()
                        self.assertEqual(first.result()[1]["judgement"], "accepted")
                    self.assertEqual(submit("COMPILER_FAILURE", b, "b1")[1]["judgement"], "compilation_error")
                    self.assertEqual(submit("WRONG", c, "c1")[1]["judgement"], "wrong_answer")
                    progress = request(base, root + "/progress", **teacher)[1]
                    self.assertEqual((progress["accepted"], progress["failed"], progress["attempts"]), (1, 2, 3))
                    self.assertEqual(progress["errorGroups"][0]["category"], "missing_semicolon")
                    self.assertEqual([(row["passed"], row["failed"]) for row in progress["caseStats"]],
                                     [(1, 1), (2, 0)])
                    result = request(base, root + "/task", **c)[1]["latestResult"]
                    self.assertNotIn("HIDDEN_NAME", json.dumps(result))
                    self.assertEqual(result["cases"][0]["actualOutput"], "-1\r\n")
                    self.assertEqual(result["cases"][1], {"name": "隐藏测试 1", "status": "passed"})
                    self.assertEqual(submit("INVALID", a, "a2")[1]["judgement"], "judge_error")
                    self.assertEqual(submit("JUDGE_FAILURE", a, "a3")[1]["judgement"], "judge_error")
                    self.assertEqual(request(base, root + "/progress", **teacher)[1]["accepted"], 0)

                self.assertEqual(run()[0], 503)
                self.assertEqual(submit("CORRECT", a, "a4")[1]["judgement"], "judge_unavailable")
                with mock(socket):
                    self.assertEqual(run()[1]["status"], "success")
                    self.assertEqual(submit("CORRECT", a, "a5")[1]["judgement"], "accepted")

            with server(data, socket) as base:
                saved = request(base, root + "/progress", **teacher)[1]
                self.assertEqual((saved["accepted"], saved["submitted"], saved["attempts"]), (1, 3, 7))
                self.assertFalse(saved["executionAvailable"])
                self.assertNotIn("HIDDEN_", json.dumps(request(base, root + "/task", **a)[1]))

    def test_interrupted_result_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "state.json"
            room, task = "a" * 32, "b" * 32
            record = {"taskId": task, "receivedAt": 1, "code": "fixture",
                      "judgement": {"status": "pending"}}
            data.write_text(json.dumps({room: {
                "name": "Interrupted", "teacherKey": "fixture",
                "tasks": [{"id": task, "title": "t", "description": "d", "starterCode": ""}],
                "students": {"test": {"name": "Tester", "number": 1, "submissions": [record]}}}}))
            with server(data) as base:
                _, state = request(base, f"/api/rooms/{room}/progress", **{"X-Teacher-Key": "fixture"})
                self.assertEqual((state["pending"], state["unjudged"]), (0, 1))
                self.assertEqual(state["students"][0]["latestStatus"], "judge_error")


if __name__ == "__main__":
    unittest.main()
