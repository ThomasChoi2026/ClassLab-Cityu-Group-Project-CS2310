"""API tests for the isolated replay demo. Never compiles or runs submitted source."""
import json
import os
import re
import select
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from judge_protocol import wait_for
from workflow import BINARY, request, server

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from demo.run import ADD, INPUTS, SUBTRACT, SYNTAX, fixture_socket


class ClassroomDemo(unittest.TestCase):
    def test_launcher_keeps_normal_data_and_cleans_up(self):
        launcher = Path(__file__).resolve().parents[1] / "demo/run.py"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / "classrooms.json"
            existing.write_text('{"ordinary": true}')
            env = dict(os.environ, TMPDIR=str(root), CLASSLAB_DATA=str(existing))
            with subprocess.Popen([sys.executable, str(launcher), "--binary", BINARY, "--port", "0"],
                                  env=env, stdout=subprocess.PIPE) as process:
                try:
                    lines = []
                    while len(lines) < 2:
                        ready, _, _ = select.select([process.stdout], [], [], 5)
                        self.assertTrue(ready, "demo server did not start")
                        chunk = os.read(process.stdout.fileno(), 512)
                        self.assertTrue(chunk, "demo server stopped before starting")
                        lines = (b"".join(lines) + chunk).splitlines(keepends=True)
                    address = re.search(rb"127\.0\.0\.1:\d+", b"".join(lines))
                    self.assertIsNotNone(address)
                    base = "http://" + address[0].decode()
                    self.assertEqual(request(base, "/api/rooms", {"name": "Temporary"})[0], 201)
                    self.assertTrue(any(root.glob("classlab-demo-*/classrooms.json")))
                    self.assertEqual(existing.read_text(), '{"ordinary": true}')
                finally:
                    if process.poll() is None:
                        process.send_signal(signal.SIGINT)
                        try:
                            process.wait(timeout=8)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
            self.assertEqual(process.returncode, 0)
            self.assertEqual(list(root.iterdir()), [existing])

    def test_replay_and_isolation(self):
        for demo in (True, False):
            with self.subTest(demo=demo), tempfile.TemporaryDirectory() as directory:
                socket = Path(directory) / "fixtures.sock"
                data = Path(directory) / "classrooms.json"
                with fixture_socket(socket), server(data, socket, demo=demo) as base:
                    self.assertEqual(request(base, "/api/health")[1].get("demo", False), demo)
                    self.assertEqual(request(base, "/demo-notebook.ipynb")[0], 200 if demo else 404)
                    _, room = request(base, "/api/rooms", {"name": "Demo Class"})
                    root = "/api/rooms/" + room["id"]
                    teacher = {"X-Teacher-Key": room["teacherKey"]}
                    cases = [{"name": f"Sample {i}", "input": value, "expectedOutput": output,
                              "visibility": "hidden" if i == 2 else "public"}
                             for i, (value, output) in enumerate(zip(INPUTS, ["5", "0", "5"]))]
                    _, task = request(base, root + "/tasks", {"title": "Add", "description": "Fix it",
                        "starterCode": SUBTRACT, "testCases": cases}, **teacher)
                    for code, outcome in [(ADD, "accepted"), (SYNTAX, "compilation_error"),
                                          (SUBTRACT, "wrong_answer"), ("int main() {}", "demo_no_fixture")]:
                        _, student = request(base, root + "/students", {"name": outcome})
                        headers = {"X-Student-Key": student["studentKey"]}
                        if demo:
                            status, first = request(base, root + "/run",
                                {"taskId": task["id"], "input": "", "probe": True, "code": code}, **headers)
                            self.assertEqual(status, 200)
                            self.assertTrue(first["demoFixture"])
                            self.assertEqual(first["status"],
                                "compilation_error" if code == SYNTAX else
                                "demo_no_fixture" if code == "int main() {}" else "stdin_required")
                            if code in (ADD, SUBTRACT):
                                status, replay = request(base, root + "/run",
                                    {"taskId": task["id"], "input": "2 3", "probe": False, "code": code}, **headers)
                                self.assertEqual((status, replay["status"], replay["stdout"]),
                                    (200, "success", "5\\n" if code == ADD else "-1\\n"))
                                self.assertTrue(replay["demoFixture"])
                                self.assertEqual(request(base, root + "/run",
                                    {"taskId": task["id"], "input": "9 9", "code": code}, **headers)[1]["status"],
                                    "demo_no_fixture")
                            self.assertEqual(request(base, root + "/run",
                                {"taskId": task["id"], "input": "", "probe": True, "code": code})[0], 403)
                        else:
                            self.assertEqual(request(base, root + "/run",
                                {"taskId": task["id"], "input": "2 3", "code": code}, **headers)[0], 503)
                        self.assertEqual(request(base, root + "/submissions",
                            {"taskId": task["id"], "code": code}, **headers)[1]["judgement"], "queued")
                        if demo:
                            state = wait_for(lambda: request(base, root + "/task", **headers)[1],
                                lambda item: item["latestResult"]["status"] == outcome)
                            self.assertTrue(state["latestResult"]["demoFixture"])
                            self.assertTrue(state["executionAvailable"])
                            self.assertNotIn("-4 9", json.dumps(state))
                    report = request(base, root + "/progress", **teacher)[1]
                    self.assertEqual((report["submitted"], report["joined"]), (4, 4))
                    self.assertEqual((report["accepted"], report["failed"], report["queued"]),
                                     (1, 2, 0) if demo else (0, 0, 4))
                    if demo:
                        self.assertEqual(report["errorGroups"][0]["category"], "missing_semicolon")
                    self.assertEqual(request(base, root + "/progress")[0], 403)


if __name__ == "__main__":
    unittest.main()
