"""Classroom API with real execution of fixed, trusted fixtures over a private socket."""
import argparse
import contextlib
import json
import socketserver
import tempfile
import threading
from pathlib import Path

from workflow import request, server
from judge_protocol import Handler, wait_for
from judge_smoke import ADD, SEMICOLON, SUBTRACT, worker

FORMAL_INPUTS = ("2 3", "0 0", "-4 9")


class TrustedFixtureHandler(Handler):
    def do_POST(self):
        assert self.path == "/evaluate"
        packet = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        code, inputs, mode = packet["code"], tuple(packet["inputs"]), packet["mode"]
        # This test cannot evaluate arbitrary source or stdin, even if contacted locally.
        allowed = (mode == "grade" and inputs == FORMAL_INPUTS and code in {ADD, SEMICOLON, SUBTRACT})
        allowed = allowed or (mode == "run" and code == ADD and inputs == ("5 3",))
        if not allowed:
            self.send_error(403)
            return
        self.reply(worker.evaluate(code, inputs, mode))


class FixtureServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    pass


@contextlib.contextmanager
def trusted_fixtures(path):
    with FixtureServer(str(path), TrustedFixtureHandler) as instance:
        thread = threading.Thread(target=instance.serve_forever)
        thread.start()
        try:
            yield
        finally:
            instance.shutdown()
            thread.join()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", choices=("runsc", "runc"), default=worker.RUNTIME)
    worker.RUNTIME = parser.parse_args().runtime
    if not Path(worker.DOCKER[0]).is_file():
        worker.DOCKER[0] = "/usr/bin/docker"
    with tempfile.TemporaryDirectory() as temp:
        directory = Path(temp)
        socket = directory / "judge.sock"
        with trusted_fixtures(socket), server(directory / "classrooms.json", socket) as base:
            _, room = request(base, "/api/rooms", {"name": "Trusted fixtures"})
            root = "/api/rooms/" + room["id"]
            teacher = {"X-Teacher-Key": room["teacherKey"]}
            _, task = request(base, root + "/tasks", {"title": "Sum", "description": "Sum", "starterCode": "",
                "testCases": [
                    {"name": "Basic", "input": FORMAL_INPUTS[0], "expectedOutput": "5", "visibility": "public"},
                    {"name": "Zero", "input": FORMAL_INPUTS[1], "expectedOutput": "0", "visibility": "public"},
                    {"name": "HIDDEN_NAME", "input": FORMAL_INPUTS[2], "expectedOutput": "5", "visibility": "hidden"},
                ]}, **teacher)
            for number, (code, expected) in enumerate(zip((ADD, SEMICOLON, SUBTRACT),
                    ("accepted", "compilation_error", "wrong_answer"))):
                _, student = request(base, root + "/students", {"name": f"Fixture {number}"})
                headers = {"X-Student-Key": student["studentKey"]}
                if number == 0:
                    response, result = request(base, root + "/run",
                        {"taskId": task["id"], "code": code, "input": "5 3"}, timeout=100, **headers)
                    assert response == 200 and result["stdout"] == "8\n", result
                status, result = request(base, root + "/submissions",
                    {"taskId": task["id"], "code": code}, timeout=110, **headers)
                assert status == 201 and result["judgement"] == "queued", result
                current = wait_for(lambda: request(base, root + "/task", **headers)[1],
                    lambda view: view["latestResult"] and view["latestResult"]["status"] == expected, timeout=105)
                assert "HIDDEN_NAME" not in json.dumps(current)
            _, progress = request(base, root + "/progress", **teacher)
            assert (progress["joined"], progress["submitted"], progress["accepted"], progress["failed"],
                    progress["attempts"]) == (3, 3, 1, 2, 3), progress
            assert progress["errorGroups"][0]["category"] == "missing_semicolon", progress
            assert [(item["passed"], item["failed"]) for item in progress["caseStats"]] == [
                (1, 1), (2, 0), (1, 1)], progress
    print("Real trusted-fixture API flow: Run stdout, accepted, compilation error, wrong answer, classroom aggregation.")


if __name__ == "__main__":
    main()
