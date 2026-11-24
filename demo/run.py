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

def score_fixtures():
    """Trusted, offline-validated fixture table. Never evaluate submitted source."""
    notebook = json.loads((ROOT / "examples/CS2310_Score_Analysis.ipynb").read_text(encoding="utf-8"))
    references = json.loads((ROOT / "examples/score_analysis_references.json").read_text(encoding="utf-8"))
    result = {}
    for reference in references.values():
        cell = notebook["cells"][reference["cell"] - 1]
        starter = "".join(cell["source"]).strip()
        if starter.startswith("%%cpp\n"):
            starter = starter[len("%%cpp\n"):].strip()
        cases = cell["metadata"]["classlab"]["testCases"]
        inputs = [case["input"] for case in cases]
        public = {case["input"] for case in cases if case["visibility"] == "public"}
        for code, outputs in [(starter, reference["starterOutputs"]),
                              (reference["referenceSource"].strip(), [case["expectedOutput"] for case in cases])]:
            if code in result or len(outputs) != len(inputs) or len(set(inputs)) != len(inputs):
                raise ValueError("Invalid or duplicate score-analysis fixture")
            result[code] = {"inputs": inputs, "outputs": outputs, "public": public}
    return result


SCORE_FIXTURES = score_fixtures()


def fixture_case(output):
    return {"status": "success", "stdoutHex": output.encode().hex(), "exitCode": 0, "stderr": ""}


def score_playback(fixture, mode, inputs):
    if mode == "probe" and inputs == [""]:
        return {"status": "stdin_required", "stdoutHex": "", "stderr": ""}
    if mode == "run" and len(inputs) == 1 and isinstance(inputs[0], str) and inputs[0] in fixture["public"]:
        return {"status": "success", "cases": [fixture_case(fixture["outputs"][fixture["inputs"].index(inputs[0])])]}
    if mode == "grade" and inputs == fixture["inputs"]:
        return {"status": "success", "cases": [fixture_case(output) for output in fixture["outputs"]]}
    return {"status": "demo_no_fixture"}



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
            mode = payload["mode"]
            inputs = payload["inputs"]
            if payload["version"] != 1 or mode not in ("grade", "probe", "run") or not isinstance(inputs, list):
                self.send_json(400, {"status": "judge_error"})
            elif code in SCORE_FIXTURES:
                self.send_json(200, score_playback(SCORE_FIXTURES[code], mode, inputs))
            elif code not in FIXTURE_OUTPUTS and code != SYNTAX.strip():
                self.send_json(200, {"status": "demo_no_fixture"})
            elif mode == "probe":
                if inputs != [""]:
                    self.send_json(400, {"status": "judge_error"})
                elif code == SYNTAX.strip():
                    self.send_json(200, {"status": "compilation_error",
                        "diagnostic": "main.cpp:5: error: expected ';' before 'std' (preloaded demo diagnostic)"})
                else:
                    self.send_json(200, {"status": "stdin_required", "stdoutHex": "", "stderr": ""})
            elif mode == "run":
                if len(inputs) != 1 or inputs[0] not in INPUTS:
                    self.send_json(200, {"status": "demo_no_fixture"})
                elif code == SYNTAX.strip():
                    self.send_json(200, {"status": "compilation_error",
                        "diagnostic": "main.cpp:5: error: expected ';' before 'std' (preloaded demo diagnostic)"})
                else:
                    output = FIXTURE_OUTPUTS[code][INPUTS.index(inputs[0])]
                    self.send_json(200, {"status": "success",
                        "cases": [{"status": "success", "stdoutHex": output.encode().hex(), "exitCode": 0,
                                   "stderr": ""}]})
            elif inputs != INPUTS:
                self.send_json(200, {"status": "demo_no_fixture"})
            elif code == SYNTAX.strip():
                self.send_json(200, {"status": "compilation_error",
                    "diagnostic": "main.cpp:5: error: expected ';' before 'std' (preloaded demo diagnostic)"})
            else:
                cases = [{"status": "success", "stdoutHex": output.encode().hex(), "exitCode": 0}
                         for output in FIXTURE_OUTPUTS[code]]
                self.send_json(200, {"status": "success", "cases": cases})
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
