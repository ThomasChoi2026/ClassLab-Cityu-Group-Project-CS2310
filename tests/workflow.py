"""Exercise the running C++ server with isolated classroom data."""
import concurrent.futures
import contextlib
import json
import os
import select
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

BINARY = str(Path(sys.argv.pop(1)).resolve())


@contextlib.contextmanager
def server(data):
    settings = dict(os.environ, CLASSLAB_DATA=str(data), CLASSLAB_PORT="0",
                    CLASSLAB_HOST="127.0.0.1")
    with subprocess.Popen([BINARY], stdout=subprocess.PIPE, text=True, env=settings) as process:
        try:
            ready, _, _ = select.select([process.stdout], [], [], 10)
            if not ready:
                raise RuntimeError("ClassLab failed to start within 10 seconds")
            address = process.stdout.readline().strip()
            if not address.startswith("ClassLab listening on 127.0.0.1:"):
                raise RuntimeError(f"ClassLab did not report a listen address: {address}")
            yield "http://" + address.split()[-1]
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def request(base, path, data=None, **headers):
    payload = None if data is None else json.dumps(data).encode()
    if payload is not None:
        headers["Content-Type"] = "application/json"
    call = urllib.request.Request(base + path, data=payload, headers=headers)
    try:
        response = urllib.request.urlopen(call, timeout=5)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        content = response.read().decode()
        if response.headers.get_content_type() == "application/json":
            content = json.loads(content)
        return response.status, content


class ClassroomWorkflow(unittest.TestCase):
    def test_classroom_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "classrooms.json"
            task = {"title": "修正返回值", "description": "让 main 返回 0。",
                    "starterCode": "int main() { return 1; }"}

            with server(data) as base:
                self.assertEqual(request(base, "/api/health"), (200, {"status": "ready"}))
                teacher_page = request(base, "/")[1]
                self.assertIn('id="create"', teacher_page)
                self.assertIn('src="/vendor/qrcode.js"', teacher_page)
                self.assertIn('id="qr-dialog"', teacher_page)
                status, asset = request(base, "/vendor/qrcode.js")
                self.assertEqual(status, 200)
                self.assertIn("QR Code Generator for JavaScript", asset)
                self.assertEqual(request(base, "/api/rooms", {"name": " "})[0], 400)
                status, room = request(base, "/api/rooms", {"name": "C++ 实验课"})
                self.assertEqual(status, 201)
                root = "/api/rooms/" + room["id"]
                teacher = {"X-Teacher-Key": room["teacherKey"]}
                self.assertIn('id="join"', request(base, "/join/" + room["id"])[1])
                self.assertEqual(request(base, root + "/progress")[0], 403)
                self.assertEqual(request(base, root + "/tasks", task)[0], 403)
                self.assertEqual(request(base, root + "/task")[0], 403)
                self.assertEqual(request(base, "/api/rooms/" + "0" * 32 + "/students",
                                         {"name": "Unknown"})[0], 404)

                status, student = request(base, root + "/students", {"name": "Ada"})
                self.assertEqual(status, 201)
                ada = {"X-Student-Key": student["studentKey"]}
                status, second = request(base, root + "/students", {"name": "Lin"})
                self.assertEqual(status, 201)
                lin = {"X-Student-Key": second["studentKey"]}
                self.assertIsNone(request(base, root + "/task", **ada)[1]["task"])

                status, current = request(base, root + "/tasks", task, **teacher)
                self.assertEqual(status, 201)
                self.assertEqual(request(base, root + "/task", **lin)[1]["task"], current)
                self.assertEqual({key: current[key] for key in task}, task)
                submission = {"taskId": current["id"], "code": "int main() { return 0; }"}
                self.assertEqual(request(base, root + "/submissions", submission)[0], 403)
                self.assertEqual(request(base, root + "/progress", **ada)[0], 403)

                # Simultaneous attempts by one student count once toward participation.
                with concurrent.futures.ThreadPoolExecutor() as workers:
                    results = list(workers.map(
                        lambda _: request(base, root + "/submissions", submission, **ada), range(4)
                    ))
                for status, receipt in results:
                    self.assertEqual(status, 201)
                    self.assertEqual(set(receipt), {"status", "receivedAt"})
                    self.assertEqual(receipt["status"], "received")

                status, stats = request(base, root + "/progress", **teacher)
                self.assertEqual(status, 200)
                self.assertEqual((stats["joined"], stats["submitted"], stats["attempts"]), (2, 1, 4))
                self.assertEqual([(row["name"], row["count"]) for row in stats["students"]],
                                 [("Ada", 4), ("Lin", 0)])

            with server(data) as base:
                self.assertEqual(request(base, root + "/progress", **teacher)[1], stats)
                self.assertEqual(request(base, root + "/task", **ada)[1]["task"], current)
                self.assertNotIn(room["teacherKey"], json.dumps(stats))
                saved = json.loads(data.read_text())[room["id"]]["students"][student["studentKey"]]
                self.assertEqual([item["code"] for item in saved["submissions"]], [submission["code"]] * 4)
                self.assertEqual(request(base, root + "/tasks", task, **teacher)[0], 201)
                self.assertEqual(request(base, root + "/submissions", submission, **ada)[0], 409)
                fresh = request(base, root + "/progress", **teacher)[1]
                self.assertEqual((fresh["joined"], fresh["submitted"], fresh["attempts"]), (2, 0, 0))


    def test_cases_privacy_and_unavailable_execution(self):
        public = {"name": "Basic case", "input": "2 3", "expectedOutput": "5", "visibility": "public"}
        hidden = {"name": "PRIVATE_CASE_NAME", "input": "PRIVATE_IN",
                  "expectedOutput": "PRIVATE_EXPECTED", "visibility": "hidden"}
        task = {"title": "Sum", "description": "Add two numbers", "starterCode": "int main() {}"}
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "classrooms.json"
            with server(data) as base:
                _, room = request(base, "/api/rooms", {"name": "Testing"})
                root = "/api/rooms/" + room["id"]
                teacher = {"X-Teacher-Key": room["teacherKey"]}
                _, first = request(base, root + "/students", {"name": "Ada"})
                _, second = request(base, root + "/students", {"name": "Lin"})
                ada = {"X-Student-Key": first["studentKey"]}
                lin = {"X-Student-Key": second["studentKey"]}
                for cases in [[], None, [dict(public, name=" ")], [dict(public, visibility="other")],
                              [dict(public, input="x" * 8193)], [public] * 13]:
                    self.assertEqual(request(base, root + "/tasks", dict(task, testCases=cases), **teacher)[0], 400)
                self.assertEqual(request(base, root + "/tasks", dict(task, testCases=[public]), **ada)[0], 403)
                status, current = request(base, root + "/tasks", dict(task, testCases=[public, hidden]), **teacher)
                self.assertEqual(status, 201)
                task_id = current["id"]
                self.assertEqual(current["testCases"][1]["input"], hidden["input"])
                student_state = request(base, root + "/task", **ada)[1]
                self.assertFalse(student_state["executionAvailable"])
                self.assertEqual(student_state["task"]["testCases"], [
                    {"name": "Basic case", "input": "2 3", "expectedOutput": "5"}])
                self.assertNotIn("PRIVATE_", json.dumps(student_state))

                code = "int main() { return 0; }"
                run = {"taskId": task_id, "code": code, "input": "8 7"}
                self.assertEqual(request(base, root + "/run", run)[0], 403)
                status, response = request(base, root + "/run", run, **ada)
                self.assertEqual((status, response["status"]), (503, "judge_unavailable"))
                self.assertEqual(request(base, root + "/progress", **teacher)[1]["attempts"], 0)

                submit = {"taskId": task_id, "code": code, "requestId": "client-attempt"}
                with concurrent.futures.ThreadPoolExecutor() as workers:
                    attempts = list(workers.map(lambda who: request(base, root + "/submissions",
                                                                    submit, **who), [ada, ada, lin]))
                for status, receipt in attempts:
                    self.assertEqual((status, receipt["judgement"]), (201, "judge_unavailable"))
                self.assertEqual(attempts[0], attempts[1])
                self.assertEqual(request(base, root + "/submissions", dict(submit, code="different"), **ada)[0], 409)
                self.assertEqual(request(base, root + "/submissions", dict(submit, requestId="another"), **ada)[0], 201)
                progress = request(base, root + "/progress", **teacher)[1]
                self.assertEqual((progress["attempts"], progress["submitted"], progress["unjudged"]), (3, 2, 2))
                self.assertEqual((progress["accepted"], progress["failed"], progress["pending"]), (0, 0, 0))
                self.assertEqual(progress["errorGroups"], [])
                self.assertTrue(all(test["passed"] == test["failed"] == 0 for test in progress["caseStats"]))
                detail = root + "/latest/1?taskId=" + task_id
                self.assertEqual(request(base, detail, **lin)[0], 403)
                self.assertEqual(request(base, detail, **teacher)[1]["code"], code)
                self.assertEqual(request(base, root + "/task", **ada)[1]["latestResult"]["status"], "judge_unavailable")

            with server(data) as base:
                self.assertEqual(request(base, root + "/progress", **teacher)[1], progress)
                status, replacement = request(base, root + "/tasks", dict(task, testCases=[
                    dict(public, input="", expectedOutput="")]), **teacher)
                self.assertEqual(status, 201)
                self.assertNotEqual(replacement["id"], task_id)
                self.assertEqual(request(base, root + "/submissions", submit, **ada)[0], 409)
                self.assertEqual(request(base, detail, **teacher)[0], 409)
                self.assertIsNone(request(base, root + "/task", **ada)[1]["latestResult"])
            self.assertEqual(json.loads(data.read_text())[room["id"]]["tasks"][0], current)

    def test_saved_result_fixture_projection_and_statistics(self):
        # Synthetic records exercise display and permissions without executing code.
        room_id = "a" * 32
        task_id = "b" * 32
        teacher = {"X-Teacher-Key": "teacher-fixture"}
        task = {"id": task_id, "title": "Fixture", "description": "Test data", "starterCode": "",
                "testCases": [{"id": "1", "name": "Public", "input": "p", "expectedOutput": "3",
                               "visibility": "public"},
                              {"id": "2", "name": "PRIVATE_NAME", "input": "PRIVATE_INPUT",
                               "expectedOutput": "PRIVATE_EXPECTED", "visibility": "hidden"}]}

        def attempt(status, **extra):
            return {"taskId": task_id, "code": "fixture source", "receivedAt": 1,
                    "judgement": {"status": status, **extra}}

        def student(number, *submissions):
            return {"number": number, "name": f"Student {number}", "submissions": submissions}

        wrong = attempt("wrong_answer", passed=1, total=2, cases=[
            {"testId": "1", "status": "passed", "actualOutput": "3"},
            {"testId": "2", "status": "wrong_answer", "actualOutput": "PRIVATE_ACTUAL",
             "diagnostic": "PRIVATE_STDERR"}])
        accepted = attempt("accepted", passed=2, total=2, cases=[
            {"testId": "1", "status": "passed"}, {"testId": "2", "status": "passed"}])
        compile_error = attempt("compilation_error", diagnostic="file.cpp:3:4: error: expected ';' before '}'")
        students = {"ada": student(1, accepted, wrong), "lin": student(2, compile_error),
                    "lee": student(3, compile_error), "ann": student(4, accepted),
                    "bob": student(5, attempt("judge_error")), "cal": student(6)}
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "classrooms.json"
            data.write_text(json.dumps({room_id: {"teacherKey": teacher["X-Teacher-Key"],
                "name": "Fixture room", "tasks": [task], "students": students}}))
            root = "/api/rooms/" + room_id
            with server(data) as base:
                progress = request(base, root + "/progress", **teacher)[1]
                self.assertEqual((progress["accepted"], progress["failed"], progress["unjudged"],
                                  progress["unsubmitted"], progress["attempts"]), (1, 3, 1, 1, 6))
                self.assertEqual([(case["passed"], case["failed"]) for case in progress["caseStats"]],
                                 [(2, 0), (1, 1)])
                self.assertEqual(progress["errorGroups"], [{"category": "missing_semicolon", "count": 2,
                    "example": "expected ';' before '}'", "studentNumber": 2}])
                result = request(base, root + "/task", **{"X-Student-Key": "ada"})[1]
                self.assertNotIn("PRIVATE_", json.dumps(result))
                self.assertNotIn("fixture source", json.dumps(result))
                self.assertEqual(result["latestResult"]["cases"], [
                    {"status": "passed", "name": "Public", "input": "p", "expectedOutput": "3", "actualOutput": "3"},
                    {"name": "隐藏测试 1", "status": "wrong_answer"}])
                detail = root + "/latest/2?taskId=" + task_id
                self.assertEqual(request(base, detail, **{"X-Student-Key": "lin"})[0], 403)
                self.assertEqual(request(base, detail, **teacher)[1]["result"], compile_error["judgement"])

    def test_failed_write_keeps_last_saved_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "classrooms.json"
            with server(data) as base:
                status, room = request(base, "/api/rooms", {"name": "Existing class"})
                self.assertEqual(status, 201)
                before = data.read_bytes()
                blocked = data.with_suffix(".json.tmp")
                blocked.mkdir()
                sentinel = blocked / "keep"
                sentinel.write_text("block temporary file creation")
                root = "/api/rooms/" + room["id"]
                self.assertEqual(request(base, root + "/students", {"name": "Ada"})[0], 500)
                self.assertEqual(data.read_bytes(), before)
                teacher = {"X-Teacher-Key": room["teacherKey"]}
                self.assertEqual(request(base, root + "/progress", **teacher)[1]["joined"], 0)

                sentinel.unlink()
                blocked.rmdir()
                self.assertEqual(request(base, root + "/students", {"name": "Ada"})[0], 201)
                self.assertEqual(request(base, root + "/progress", **teacher)[1]["joined"], 1)


if __name__ == "__main__":
    unittest.main()
