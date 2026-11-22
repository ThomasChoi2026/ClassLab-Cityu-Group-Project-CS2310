"""HTTP/Unix transport tests with a mock Judge. No student code is executed."""
import concurrent.futures
import contextlib
import http.server
import json
import socketserver
import tempfile
import threading
import time
import unittest
from pathlib import Path

from workflow import request, server


def wait_for(read, predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while True:
        result = read()
        if predicate(result):
            return result
        if time.monotonic() >= deadline:
            raise AssertionError(f"condition did not become true: {result}")
        time.sleep(0.05)


class MockServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    def __init__(self, path):
        self.started = threading.Event()
        self.release = threading.Event()
        self.evaluated = []
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
        if packet["mode"] == "grade":
            self.server.evaluated.append(code)
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

                def progress():
                    return request(base, root + "/progress", **teacher)[1]

                def expect(student, expected):
                    return wait_for(lambda: request(base, root + "/task", **student)[1]["latestResult"],
                                    lambda result: result and result["status"] == expected)

                self.assertEqual(run()[0], 503)
                with mock(socket) as worker:
                    status, result = run()
                    self.assertEqual((status, result["stdout"], result["stderr"], result["exitCode"]),
                                     (200, "8\r\n", "mock stderr", 0))
                    self.assertEqual(request(base, root + "/progress", **teacher)[1]["attempts"], 0)
                    self.assertEqual(submit("HOLD", a, "a1")[1]["judgement"], "queued")
                    self.assertTrue(worker.started.wait(2))
                    self.assertEqual(progress()["pending"], 1)
                    self.assertEqual(submit("COMPILER_FAILURE", b, "b1")[1]["judgement"], "queued")
                    self.assertEqual(submit("HOLD", a, "a1")[1]["judgement"], "pending")
                    self.assertEqual(progress()["queued"], 1)
                    worker.release.set()
                    self.assertEqual(submit("WRONG", c, "c1")[1]["judgement"], "queued")
                    expect(a, "accepted")
                    expect(b, "compilation_error")
                    result = expect(c, "wrong_answer")
                    state = progress()
                    self.assertEqual((state["accepted"], state["failed"], state["attempts"]), (1, 2, 3))
                    self.assertEqual(state["errorGroups"][0]["category"], "missing_semicolon")
                    self.assertEqual([(row["passed"], row["failed"]) for row in state["caseStats"]],
                                     [(1, 1), (2, 0)])
                    self.assertNotIn("HIDDEN_NAME", json.dumps(result))
                    self.assertEqual(result["cases"][0]["actualOutput"], "-1\r\n")
                    self.assertEqual(result["cases"][1], {"name": "隐藏测试 1", "status": "passed"})
                    self.assertEqual(submit("INVALID", a, "a2")[1]["judgement"], "queued")
                    expect(a, "judge_error")
                    self.assertEqual(submit("JUDGE_FAILURE", a, "a3")[1]["judgement"], "queued")
                    wait_for(progress, lambda report: report["queued"] == report["pending"] == 0)
                    expect(a, "judge_error")
                    self.assertEqual(progress()["accepted"], 0)

                self.assertEqual(run()[0], 503)
                self.assertEqual(submit("CORRECT", a, "a4")[1]["judgement"], "queued")
                self.assertEqual(progress()["queued"], 1)
                with mock(socket):
                    expect(a, "accepted")
                    self.assertEqual(run()[1]["status"], "success")
                    self.assertEqual(submit("CORRECT", a, "a5")[1]["judgement"], "queued")
                    expect(a, "accepted")

            with server(data, socket) as base:
                saved = request(base, root + "/progress", **teacher)[1]
                self.assertEqual((saved["accepted"], saved["submitted"], saved["attempts"]), (1, 3, 7))
                self.assertFalse(saved["executionAvailable"])
                self.assertNotIn("HIDDEN_", json.dumps(request(base, root + "/task", **a)[1]))

    def test_thirty_students_fifo_and_latest_result(self):
        with tempfile.TemporaryDirectory() as directory:
            socket = Path(directory) / "judge.sock"
            data = Path(directory) / "state.json"
            with mock(socket) as worker, server(data, socket) as base:
                root, teacher, task, students = self.make_class(base, 30)

                def submit(index, code, req):
                    return request(base, root + "/submissions",
                                   {"taskId": task, "code": code, "requestId": req}, **students[index])

                self.assertEqual(submit(0, "HOLD", "original")[1]["judgement"], "queued")
                self.assertTrue(worker.started.wait(2))
                with concurrent.futures.ThreadPoolExecutor(max_workers=30) as pool:
                    responses = list(pool.map(lambda i: submit(i, "WRONG" if i == 0 else f"CODE-{i}",
                                                               f"latest-{i}"), range(30)))
                self.assertTrue(all(status == 201 and body["judgement"] == "queued" for status, body in responses))
                state = request(base, root + "/progress", **teacher)[1]
                self.assertEqual((state["queued"], state["submitted"], state["attempts"]), (30, 30, 31))
                queued = [item for student in next(iter(json.loads(data.read_text()).values()))["students"].values()
                          for item in student["submissions"] if item["judgement"]["status"] == "queued"]
                expected = [item["code"] for item in sorted(queued, key=lambda item: item["queueSequence"])]
                worker.release.set()
                final = wait_for(lambda: request(base, root + "/progress", **teacher)[1],
                                 lambda report: report["accepted"] == 29 and report["failed"] == 1)
                self.assertEqual(worker.evaluated, ["HOLD", *expected])
                self.assertEqual(final["students"][0]["latestStatus"], "wrong_answer")
                self.assertEqual(final["students"][0]["count"], 2)

    def test_task_change_during_grading_uses_original_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            socket = Path(directory) / "judge.sock"
            data = Path(directory) / "state.json"
            with mock(socket) as worker, server(data, socket) as base:
                root, teacher, task, students = self.make_class(base, 1)
                student = students[0]
                status, _ = request(base, root + "/submissions", {"taskId": task, "code": "HOLD"}, **student)
                self.assertEqual(status, 201)
                self.assertTrue(worker.started.wait(2))
                _, replacement = request(base, root + "/tasks",
                    {"title": "New", "description": "New", "starterCode": "", "testCases": [
                        {"name": "New equality", "input": "0 0", "expectedOutput": "0", "visibility": "public"}
                    ]}, **teacher)
                self.assertEqual(request(base, root + "/submissions", {"taskId": task, "code": "HOLD"}, **student)[0], 409)
                request(base, root + "/submissions", {"taskId": replacement["id"], "code": "CORRECT"}, **student)
                worker.release.set()
                report = wait_for(lambda: request(base, root + "/progress", **teacher)[1],
                                  lambda view: view["accepted"] == 1)
                self.assertEqual((report["submitted"], report["attempts"]), (1, 1))
                stored = next(iter(json.loads(data.read_text())[root.rsplit("/", 1)[-1]]["students"].values()))
                self.assertEqual([entry["judgement"]["status"] for entry in stored["submissions"]],
                                 ["accepted", "accepted"])

    def test_queue_bound_and_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            socket = Path(directory) / "judge.sock"
            data = Path(directory) / "state.json"
            with server(data, socket) as base:
                root, teacher, task, students = self.make_class(base, 1)
                student = students[0]
                for index in range(65):
                    status, result = request(base, root + "/submissions",
                        {"taskId": task, "code": f"CODE-{index}", "requestId": str(index)}, **student)
                    self.assertEqual((status, result["judgement"]),
                                     (201, "queued" if index < 64 else "judge_queue_full"))
                submitted = next(iter(json.loads(data.read_text().strip()).values()))["students"]
                self.assertEqual(len(next(iter(submitted.values()))["submissions"]), 65)

            with mock(socket) as worker, server(data, socket) as base:
                def first():
                    return worker.evaluated[0] if worker.evaluated else None

                self.assertEqual(wait_for(first, lambda value: value is not None), "CODE-0")
                wait_for(lambda: len(worker.evaluated), lambda size: size == 64)
                latest = request(base, root + "/task", **student)[1]["latestResult"]
                self.assertEqual(latest["status"], "judge_queue_full")
                self.assertEqual(request(base, root + "/progress", **teacher)[1]["attempts"], 65)

    def make_class(self, base, size):
        _, room = request(base, "/api/rooms", {"name": "Queue"})
        root = "/api/rooms/" + room["id"]
        teacher = {"X-Teacher-Key": room["teacherKey"]}
        _, task = request(base, root + "/tasks", {"title": "Sum", "description": "Sum", "starterCode": "",
            "testCases": [{"name": "Example", "input": "2 3", "expectedOutput": "5", "visibility": "public"}]},
            **teacher)
        students = []
        for index in range(size):
            _, student = request(base, root + "/students", {"name": f"Student {index}"})
            students.append({"X-Student-Key": student["studentKey"]})
        return root, teacher, task["id"], students

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
