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
