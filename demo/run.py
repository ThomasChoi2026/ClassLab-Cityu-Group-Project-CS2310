#!/usr/bin/env python3
"""Loopback demonstration using temporary data and fixed, precomputed results."""
import argparse
import json
import os
import socketserver
import subprocess
import tempfile
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ["2 3", "0 0", "-4 9"]
NOTEBOOK = json.loads((ROOT / "examples/classlab-demo.ipynb").read_text())
SUBTRACT = "".join(NOTEBOOK["cells"][1]["source"])
ADD = SUBTRACT.replace("a - b", "a + b")
SYNTAX = NOTEBOOK["cells"][2]["source"]
FIXTURE_OUTPUTS = {ADD.strip(): ["5\n", "0\n", "5\n"], SUBTRACT.strip(): ["-1\n", "0\n", "-13\n"]}


class FixtureHandler(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(3)
        super().setup()

    def log_message(self, *args):
        pass

    def send_json(self, status, content):
        body = json.dumps({"version": 1, "demoFixture": True, **content}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"status": "ready", "busy": False})
        else:
            self.send_json(404, {"status": "judge_error"})

    def do_POST(self):
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if self.path != "/evaluate" or not 0 < size <= 384 * 1024:
                self.send_json(400, {"status": "judge_error"})
                return
            payload = json.loads(self.rfile.read(size))
            code = payload["code"].strip()
            if payload["version"] != 1 or payload["mode"] != "grade" or payload["inputs"] != INPUTS:
                self.send_json(200, {"status": "demo_no_fixture"})
            elif code == SYNTAX.strip():
                self.send_json(200, {"status": "compilation_error",
                    "diagnostic": "main.cpp:5: error: expected ';' before 'std' (preloaded demo diagnostic)"})
            elif code in FIXTURE_OUTPUTS:
                cases = [{"status": "success", "stdoutHex": output.encode().hex(), "exitCode": 0}
                         for output in FIXTURE_OUTPUTS[code]]
                self.send_json(200, {"status": "success", "cases": cases})
            else:
                self.send_json(200, {"status": "demo_no_fixture"})
        except (ValueError, KeyError, TypeError, AttributeError):
            self.send_json(400, {"status": "judge_error"})


@contextmanager
def fixture_socket(path):
    with socketserver.UnixStreamServer(str(path), FixtureHandler) as server:
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            yield
        finally:
            server.shutdown()
            thread.join()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, default=ROOT / "build/classlab")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    if not args.binary.is_file() or not os.access(args.binary, os.X_OK):
        parser.error("build ClassLab first (see README.md), or pass --binary")
    with tempfile.TemporaryDirectory(prefix="classlab-demo-") as directory:
        data = Path(directory)
        socket = data / "fixtures.sock"
        settings = dict(os.environ, CLASSLAB_DEMO="1", CLASSLAB_HOST="127.0.0.1",
                        CLASSLAB_DATA=str(data / "classrooms.json"), CLASSLAB_PORT=str(args.port),
                        CLASSLAB_JUDGE_SOCKET=str(socket))
        print("ClassLab demo: fixed replay results, live classroom records, temporary storage.", flush=True)
        with fixture_socket(socket), subprocess.Popen([str(args.binary.resolve())], env=settings) as process:
            try:
                return process.wait()
            except KeyboardInterrupt:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
                return 0


if __name__ == "__main__":
    raise SystemExit(main())
