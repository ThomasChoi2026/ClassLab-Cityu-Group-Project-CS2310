#!/usr/bin/env python3
"""Real, non-container GCC execution of operator-reviewed sources ONLY.

This is not a sandbox. Never use it for arbitrary student submissions.
The classroom web server remains loopback-only and the socket is private.
No precomputed output is used. Approved source text is read from disk,
not taken from the HTTP request; all verdicts use actual GCC execution.
"""
import argparse
import contextlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import threading

import worker

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_LIMIT = 16384


def approved_sources(extra=()):
    notebook = json.loads((ROOT / "examples/CS2310_Score_Analysis.ipynb").read_text(encoding="utf-8"))
    references = json.loads((ROOT / "examples/score_analysis_references.json").read_text(encoding="utf-8"))
    sources = set()
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            source = "".join(cell["source"]).strip().removeprefix("%%cpp\n").strip()
            sources.add(source)
    sources.update(item["referenceSource"].strip() for item in references.values())
    for path in extra:
        source = Path(path).read_text(encoding="utf-8").strip()
        if not 0 < len(source.encode()) <= 65536:
            raise ValueError("Approved source length is invalid")
        sources.add(source)
    return {source: source for source in sources}


def process(args, cwd, stdin, timeout, *, compile_step=False):
    # These are basic resource limits for reviewed programs, NOT containment.
    cap = 2 * 1024 * 1024 if compile_step else 65536
    limiter = ["/usr/bin/prlimit", "--as=536870912", "--cpu=" + str(timeout),
               "--fsize=" + str(cap), "--nofile=64", "--core=0", "--"]
    environment = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "HOME": str(cwd),
                   "TMPDIR": str(cwd)}
    with tempfile.TemporaryFile(dir=cwd) as out, tempfile.TemporaryFile(dir=cwd) as err:
        child = subprocess.Popen(limiter + list(args), cwd=cwd, env=environment,
                                 stdin=stdin, stdout=out, stderr=err, start_new_session=True)
        timed_out = False
        try:
            child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            # Also terminate any remaining children in the process group.
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait()
        out.seek(0)
        err.seek(0)
        stdout = out.read(OUTPUT_LIMIT + 1)
        stderr = err.read(OUTPUT_LIMIT + 1)
    status = "time_limit" if timed_out else (
        "resource_limit" if len(stdout) > OUTPUT_LIMIT or len(stderr) > OUTPUT_LIMIT
        or child.returncode == -signal.SIGXFSZ else
        "success" if child.returncode == 0 else "runtime_error")
    return status, child.returncode, stdout[:OUTPUT_LIMIT], stderr[:OUTPUT_LIMIT]


class NativeEvaluator:
    def __init__(self, compiler, sources):
        self.compiler = str(Path(compiler).resolve())
        self.sources = dict(sources)

    def __call__(self, code, inputs, mode):
        # Reject before the compiler is invoked. Only the stored reviewed
        # source is written, not the network-provided string.
        source = self.sources.get(code.strip())
        if source is None:
            return {"status": "source_not_approved"}
        with tempfile.TemporaryDirectory(prefix="classlab-trusted-native-") as tmp:
            work = Path(tmp)
            file = work / "main.cpp"
            binary = work / "program"
            file.write_text(source + "\n", encoding="utf-8")
            with open(os.devnull, "rb") as empty:
                status, rc, _, diagnostics = process(
                    [self.compiler, "-std=c++20", "-O0", "-fdiagnostics-color=never",
                     "-fmax-errors=12", "main.cpp", "-o", str(binary)],
                    work, empty, 20, compile_step=True)
            if status != "success":
                if status in ("time_limit", "resource_limit"):
                    return {"status": status}
                if rc == 1 and diagnostics:
                    return {"status": "compilation_error", "diagnostic": diagnostics.decode(errors="replace")}
                return {"status": "judge_error"}
            if not binary.is_file():
                return {"status": "judge_error"}
            outcomes = []
            for value in inputs:
                with tempfile.TemporaryFile(dir=work) as incoming:
                    incoming.write(b"\n" if mode == "probe" else value.encode())
                    incoming.seek(0)
                    status, rc, out, err = process([str(binary)], work, incoming, 3)
                    consumed = incoming.tell() > 0
                # As in the native Judge, the probe reruns from the beginning.
                if mode == "probe" and consumed and status in ("success", "runtime_error"):
                    return {"status": "stdin_required", "stdoutHex": out.hex(),
                            "stderr": err.decode(errors="replace")}
                case = {"status": status, "stdoutHex": out.hex(), "exitCode": rc}
                if mode != "grade":
                    case["stderr"] = err.decode(errors="replace")
                outcomes.append(case)
            return {"status": "success", "cases": outcomes}


@contextlib.contextmanager
def native_socket(path, evaluator):
    original = worker.evaluate
    worker.evaluate = evaluator
    try:
        with worker.Worker(str(path)) as server:
            Path(path).chmod(0o600)
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            try:
                yield
            finally:
                server.shutdown()
                thread.join()
    finally:
        worker.evaluate = original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trusted-local-only", action="store_true",
                        help="Confirm a private, trusted, non-production session; no arbitrary student execution.")
    parser.add_argument("--binary", type=Path, default=ROOT / "build/classlab")
    parser.add_argument("--compiler", default="g++")
    parser.add_argument("--approve-source", type=Path, action="append", default=[],
                        help="Locally reviewed C++ file; its contents are pinned at startup. Never approve unreviewed code.")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--data", type=Path, default=ROOT / "data/trusted-native-classrooms.json")
    args = parser.parse_args()
    if not args.trusted_local_only:
        parser.error("This is not a sandbox. Use --trusted-local-only only for reviewed source on a private test host.")
    if os.geteuid() == 0:
        parser.error("Do not run the native test worker as root.")
    compiler = shutil.which(args.compiler)
    if not compiler or not Path("/usr/bin/prlimit").is_file() or not args.binary.is_file():
        parser.error("Build ClassLab first; Linux g++ and prlimit are required.")
    if not 1 <= args.port <= 65535:
        parser.error("Invalid port.")
    evaluator = NativeEvaluator(compiler, approved_sources(args.approve_source))
    with tempfile.TemporaryDirectory(prefix="classlab-trusted-socket-") as temp:
        socket = Path(temp) / "judge.sock"
        env = dict(os.environ, CLASSLAB_HOST="127.0.0.1", CLASSLAB_PORT=str(args.port),
                   CLASSLAB_DATA=str(args.data.resolve()), CLASSLAB_JUDGE_SOCKET=str(socket))
        env.pop("CLASSLAB_DEMO", None)
        print("Trusted native GCC: no sandbox; only operator-approved sources run. Keep port PRIVATE.", flush=True)
        with native_socket(socket, evaluator):
            with subprocess.Popen([str(args.binary.resolve())], env=env) as child:
                try:
                    return child.wait()
                except KeyboardInterrupt:
                    child.terminate()
                    return child.wait(timeout=10)


if __name__ == "__main__":
    raise SystemExit(main())
