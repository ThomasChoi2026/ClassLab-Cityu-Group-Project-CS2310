#!/usr/bin/env python3
"""Private Unix socket worker. Only its sandbox can compile or run submissions."""
import argparse
import base64
import contextlib
import http.server
import json
import os
import selectors
import socketserver
import stat
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path

IMAGE = "docker.io/library/gcc@sha256:5e927c284bf55a7dc796262e311a0703344f62f41f5621eb56843111b1d37e15"
DOCKER = ["/usr/local/bin/docker", "--host", "unix:///var/run/docker.sock"]
# A fresh CLI config prevents Docker from copying user-defined proxy variables.
CLI_CONFIG = tempfile.TemporaryDirectory(prefix="classlab-docker-config-")
DOCKER_ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C", "DOCKER_CONFIG": CLI_CONFIG.name}
RUNTIME = "runsc"
MEMORY = 256 * 1024 * 1024
OUTPUT = 16 * 1024
ARTIFACT = 1024 * 1024  # maximum encoded executable
MAX_REQUEST = 1024 * 1024
OWNER_LABEL = "org.classlab.worker=phase4"
COMPILE = """set -eu
cat > /work/main.cpp || exit 70
g++ -std=c++20 -O0 -fdiagnostics-color=never -fmax-errors=12 /work/main.cpp -o /work/program
exec base64 -w0 /work/program
"""
EXECUTE = """set -eu
IFS= read -r binary
printf '%s' "$binary" | base64 -d > /work/program
chmod 500 /work/program
exec /work/program
"""

BOUNDARY_PROBE = """set -eu
test "$(id -u)" = 65534
grep -q 'CapEff:[[:space:]]*0000000000000000' /proc/self/status
test "$(awk -F: 'NR>2 {gsub(/[[:space:]]/, "", $1); print $1}' /proc/net/dev)" = lo
test ! -S /var/run/docker.sock
test ! -e /workspace
for key in GITHUB_TOKEN GH_TOKEN SSH_AUTH_SOCK AWS_ACCESS_KEY_ID; do
    if printenv "$key" >/dev/null; then exit 1; fi
done
test -z "$(printenv | cut -d= -f1 | grep -iE '^(http|https|all)_proxy$' || true)"
awk '$2=="/" && $4~/^ro(,|$)/ {ok=1} END {exit !ok}' /proc/mounts
test "$(df -Pk /work | awk 'END {print $2}')" -le 16384
test "$(df -Pk /tmp | awk 'END {print $2}')" -le 8192
test "$(ulimit -f)" -le 1024
"""


def docker(*args, timeout=5):
    return subprocess.run([*DOCKER, *args], env=DOCKER_ENV,
                          capture_output=True, timeout=timeout, check=True).stdout


def inspect(container):
    return json.loads(docker("inspect", "--format", "{{json .State}}", container))


@contextlib.contextmanager
def container(script):
    name = "classlab-" + uuid.uuid4().hex
    try:
        docker("create", "--name", name, "--label", OWNER_LABEL, "--pull=never", "--runtime=" + RUNTIME, "--platform=linux/amd64",
               "--network=none", "--ipc=none", "--user=65534:65534", "--cap-drop=ALL",
               "--security-opt=no-new-privileges", "--read-only", "--log-driver=none",
               "--memory=256m", "--memory-swap=256m", "--cpus=1", "--pids-limit=32",
               "--ulimit", "fsize=1048576:1048576", "--ulimit", "core=0:0",
               "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=8m",
               "--tmpfs", "/work:rw,exec,nosuid,nodev,uid=65534,gid=65534,mode=0700,size=16m",
               "--workdir", "/work", "--env", "LANG=C", "--env", "LC_ALL=C",
               "--interactive", IMAGE, "/bin/bash", "-c", script, timeout=25)
        yield name
    finally:
        # Never leave a timed-out container running. A cleanup failure disables this worker.
        try:
            docker("rm", "-f", name)
        except subprocess.CalledProcessError as error:
            if b"No such container" not in error.stderr:
                raise


def collect(process, payload, timeout, stdout_cap):
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    caps = {"stdout": stdout_cap, "stderr": OUTPUT}
    pending = memoryview(payload)
    deadline = time.monotonic() + timeout
    with selectors.DefaultSelector() as selector:
        for stream in ("stdout", "stderr"):
            pipe = getattr(process, stream)
            os.set_blocking(pipe.fileno(), False)
            selector.register(pipe, selectors.EVENT_READ, stream)
        if pending:
            os.set_blocking(process.stdin.fileno(), False)
            selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
        else:
            process.stdin.close()

        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return "time_limit", buffers
            for key, _ in selector.select(remaining):
                pipe, stream = key.fileobj, key.data
                if stream == "stdin":
                    try:
                        pending = pending[os.write(pipe.fileno(), pending[:8192]):]
                    except BrokenPipeError:
                        pending = pending[len(pending):]
                    except BlockingIOError:
                        continue
                    if not pending:
                        selector.unregister(pipe)
                        pipe.close()
                else:
                    try:
                        chunk = os.read(pipe.fileno(), 4096)
                    except BlockingIOError:
                        continue
                    if not chunk:
                        selector.unregister(pipe)
                        continue
                    space = caps[stream] - len(buffers[stream])
                    buffers[stream].extend(chunk[:space])
                    if len(chunk) > space:
                        return "resource_limit", buffers

    try:
        process.wait(timeout=max(0.01, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        return "time_limit", buffers
    return None, buffers


def sandbox(script, payload, timeout, stdout_cap):
    with container(script) as name:
        with subprocess.Popen([*DOCKER, "start", "-ai", name], env=DOCKER_ENV,
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) as process:
            try:
                limited, buffers = collect(process, payload, timeout, stdout_cap)
            finally:
                if process.poll() is None:
                    process.kill()
        if limited:
            return limited, None, buffers
        state = inspect(name)
        if state["Error"] or state["Status"] != "exited":
            return "judge_error", None, buffers
        if state["OOMKilled"]:
            return "resource_limit", None, buffers
        if state["ExitCode"] in (128 + 25,):  # Linux x86-64 SIGXFSZ
            return "resource_limit", state["ExitCode"], buffers
        return None, state["ExitCode"], buffers


def text(data):
    return bytes(data).decode("utf-8", errors="replace")


def compile_source(code):
    failure, exit_code, streams = sandbox(COMPILE, code.encode(), 15, ARTIFACT)
    if failure:
        return {"status": failure}, None
    if exit_code == 1 and streams["stderr"]:
        return {"status": "compilation_error", "diagnostic": text(streams["stderr"])}, None
    if exit_code != 0:
        return {"status": "judge_error"}, None
    binary = bytes(streams["stdout"])
    try:
        if not base64.b64decode(binary, validate=True).startswith(b"\x7fELF"):
            return {"status": "judge_error"}, None
    except ValueError:
        return {"status": "judge_error"}, None
    return None, binary


def run_case(binary, input_text):
    failure, exit_code, streams = sandbox(EXECUTE, binary + b"\n" + input_text.encode(), 3, OUTPUT)
    if failure == "judge_error":
        return {"status": failure}
    status = failure or ("success" if exit_code == 0 else "runtime_error")
    result = {"status": status, "stdoutHex": streams["stdout"].hex(), "stderr": text(streams["stderr"])}
    if exit_code is not None:
        result["exitCode"] = exit_code
    return result


def evaluate(code, inputs, mode):
    job_deadline = time.monotonic() + 70
    failure, binary = compile_source(code)
    if failure:
        return failure
    outcomes = []
    for item in inputs:
        if time.monotonic() >= job_deadline:
            return {"status": "judge_error"}
        result = run_case(binary, item)
        if result["status"] == "judge_error":
            return {"status": "judge_error"}
        if mode == "grade":
            result.pop("stderr", None)
        outcomes.append(result)
    return {"status": "success", "cases": outcomes}


def verify_runtime():
    """Require actual Linux cgroup controls on a dedicated machine using a local daemon."""
    info = json.loads(docker("info", "--format", "{{json .}}"))
    runtime = info["Runtimes"].get(RUNTIME, {})
    if (info["CgroupVersion"] != "2" or info["CgroupDriver"] not in {"systemd", "cgroupfs"}
            or not runtime or runtime.get("runtimeArgs")
            or info.get("OSType") != "linux"
            or "name=seccomp,profile=builtin" not in (info.get("SecurityOptions") or [])):
        raise RuntimeError(f"{RUNTIME} with the built-in seccomp profile and active local cgroup v2 is required")
    if Path(runtime.get("path", "")).name != RUNTIME:
        raise RuntimeError("the configured Docker runtime registration is invalid")
    with container("exec sleep 12") as probe:
        docker("start", probe)
        state = inspect(probe)
        if not state["Running"] or state["Pid"] <= 0:
            raise RuntimeError("the sandbox probe did not start")
        cgroup = Path(f"/proc/{state['Pid']}/cgroup").read_text().splitlines()
        path = next(line[3:] for line in cgroup if line.startswith("0::"))
        identifier = docker("inspect", "--format", "{{.Id}}", probe).decode().strip()
        if identifier not in Path(path).parts and f"docker-{identifier}.scope" not in Path(path).parts:
            raise RuntimeError("Docker PID is not in its own identifiable cgroup")
        group = Path("/sys/fs/cgroup") / path.lstrip("/")
        cpu = (group / "cpu.max").read_text().split()
        if (cpu[0] == "max" or int(cpu[0]) > int(cpu[1])
                or (group / "memory.max").read_text().strip() != str(MEMORY)
                or (group / "memory.swap.max").read_text().strip() != "0"
                or (group / "pids.max").read_text().strip() != "32"):
            raise RuntimeError("sandbox cgroup limits do not match the execution profile")
    failure, exit_code, _ = sandbox(BOUNDARY_PROBE, b"", 4, OUTPUT)
    if failure or exit_code:
        raise RuntimeError("sandbox identity, filesystem or network probe failed")
    # Some gVisor versions omit NoNewPrivs from procfs. Query the actual task instead.
    checked = evaluate(
        "#include <sys/prctl.h>\nint main(){return prctl(PR_GET_NO_NEW_PRIVS,0,0,0,0)==1?0:1;}",
        [""], "run",
    )
    if checked["status"] != "success" or checked["cases"][0].get("exitCode") != 0:
        raise RuntimeError("sandbox no-new-privileges probe failed")


class Worker(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = False

    def __init__(self, path):
        self.available = True
        self.slot = threading.Lock()
        self.connections = threading.BoundedSemaphore(8)
        super().__init__(path, Handler)

    def process_request(self, request, address):
        if not self.connections.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except BaseException:
            self.connections.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.connections.release()


class Handler(http.server.BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(5)
        super().setup()

    def log_message(self, *_args):
        pass  # Request bodies and student data must stay out of logs.

    def respond(self, status, body):
        encoded = json.dumps({"version": 1, **body}, ensure_ascii=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        if self.path != "/health":
            return self.respond(404, {"status": "judge_error"})
        available = self.server.available
        self.respond(200 if available else 503, {"status": "ready" if available else "judge_error"})

    def do_POST(self):
        if self.path != "/evaluate":
            return self.respond(404, {"status": "judge_error"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if self.headers.get("Transfer-Encoding") or not 0 < size <= MAX_REQUEST:
                raise ValueError("invalid request size")
            payload = json.loads(self.rfile.read(size))
            code, inputs, mode = payload["code"], payload["inputs"], payload["mode"]
            if (payload["version"] != 1 or mode not in ("run", "grade") or not isinstance(code, str) or not 0 < len(code.encode()) <= 65536
                    or not isinstance(inputs, list) or not 1 <= len(inputs) <= 12
                    or (mode == "run" and len(inputs) != 1)
                    or not all(isinstance(item, str) and len(item.encode()) <= 8192 for item in inputs)):
                raise ValueError("invalid payload")
        except (ValueError, KeyError, TypeError):
            return self.respond(400, {"status": "judge_error"})
        if not self.server.slot.acquire(blocking=False):
            return self.respond(429, {"status": "busy"})
        try:
            if not self.server.available:
                return self.respond(503, {"status": "judge_error"})
            try:
                result = evaluate(code, inputs, mode)
            except (OSError, subprocess.SubprocessError, ValueError, KeyError):
                # Fail closed after an infrastructure or cleanup problem.
                self.server.available = False
                result = {"status": "judge_error"}
            self.respond(200, result)
        finally:
            self.server.slot.release()


def main():
    global RUNTIME
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", type=Path)
    parser.add_argument("--runtime", choices=("runsc", "runc"), default=RUNTIME)
    parser.add_argument("--cleanup", action="store_true")
    parser.add_argument("--operator-verified", action="store_true",
                        help="attest the deployment acceptance checks in docs/PHASE_4.md")
    args = parser.parse_args()
    RUNTIME = args.runtime
    if args.socket and not args.operator_verified:
        parser.error("serving student requests requires an operator-verified deployment")
    # docker may be installed by a system package rather than under /usr/local.
    if not Path(DOCKER[0]).exists():
        DOCKER[0] = "/usr/bin/docker"
    if args.cleanup:
        if args.socket:
            parser.error("--cleanup cannot be used while starting a worker")
        ids = docker("ps", "-aq", "--filter", "label=" + OWNER_LABEL).decode().split()
        if ids:
            docker("rm", "-f", *ids, timeout=25)
        return
    try:
        verify_runtime()
    except (OSError, RuntimeError, subprocess.SubprocessError, StopIteration) as error:
        parser.exit(2, f"Judge startup refused: {error}\n")
    if not args.socket:
        print("Sandbox startup probes passed. Complete the documented deployment tests before serving.")
        return
    parent = args.socket.parent
    metadata = parent.stat()
    mode = stat.S_IMODE(metadata.st_mode)
    if (not args.socket.is_absolute() or parent.is_symlink() or metadata.st_uid != os.getuid()
            or mode not in {0o700, 0o710}):
        parser.error("socket needs an absolute path in a worker-owned 0700 or 0710 directory")
    os.umask(0o077)
    server = Worker(str(args.socket))
    try:
        if mode == 0o710:
            os.chown(args.socket, -1, metadata.st_gid)
            args.socket.chmod(0o660)
        with server:
            server.serve_forever()
    finally:
        args.socket.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
