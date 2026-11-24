"""Bounded persistent free-Run sessions; the backend defines the execution boundary."""
import os
import secrets
import selectors
import signal
import subprocess
import threading
import time

ACTIVE = {"compiling", "running", "stopping"}
OUTPUT = 16384
INPUT = 8192


class Session:
    def __init__(self, owner, task, code, idle, wall):
        self.id = secrets.token_hex(16)
        self.owner, self.task, self.code = owner, task, code
        self.idle, self.wall = idle, wall
        self.lock = threading.Lock()
        self.cancel = threading.Event()
        self.status = "compiling"
        self.pending = bytearray()
        self.input_total = 0
        self.eof = False
        self.stdout, self.stderr = bytearray(), bytearray()
        self.extra = {}
        self.finished = None

    def snapshot(self):
        with self.lock:
            return {"sessionId": self.id, "status": self.status,
                    "stdinOpen": self.status == "running" and not self.eof,
                    "stdout": self.stdout.decode("utf-8", "replace"),
                    "stderr": self.stderr.decode("utf-8", "replace"), **self.extra}

    def action(self, action, value=""):
        with self.lock:
            if action == "stop" and self.status in ACTIVE:
                self.cancel.set()
                self.status = "stopping"
            elif action in ("input", "eof"):
                if self.status != "running" or self.eof:
                    return {"status": "input_closed", "error": "This session no longer accepts input."}
                if action == "eof":
                    self.eof = True
                else:
                    data = value.encode("utf-8")
                    if self.input_total + len(data) > INPUT:
                        return {"status": "input_limit", "error": "Session input limit: 8192 bytes."}
                    self.pending.extend(data)
                    self.input_total += len(data)
        return self.snapshot()

    def ready(self):
        with self.lock:
            if not self.cancel.is_set():
                self.status = "running"

    def append(self, name, chunk):
        with self.lock:
            output = getattr(self, name)
            space = OUTPUT - len(output)
            output.extend(chunk[:space])
            return len(chunk) <= space

    def finish(self, result):
        with self.lock:
            self.status = "stopped" if self.cancel.is_set() else result["status"]
            self.extra = {k: v for k, v in result.items() if k != "status"}
            self.finished = time.monotonic()
            self.pending.clear()
            self.eof = True
            self.code = ""


def terminate_group(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=5)


def pump(session, process, *, bootstrap=b"", ready_marker=b"", boot_timeout=12):
    """Keep the very same process and stdin pipe open until explicit EOF.
    Return a failure status or None; the backend classifies the actual exit.
    """
    pending, prefix = bytearray(bootstrap), bytearray()
    ready = not ready_marker
    start = last = time.monotonic()
    boot_deadline = start + boot_timeout
    if ready:
        session.ready()
    try:
        with selectors.DefaultSelector() as selector:
            for name in ("stdout", "stderr"):
                stream = getattr(process, name)
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            pipe = process.stdin
            os.set_blocking(pipe.fileno(), False)
            registered, read_pipes = False, 2
            while True:
                now = time.monotonic()
                if session.cancel.is_set():
                    return "stopped"
                if not ready and now >= boot_deadline:
                    return "judge_error"
                if ready and now - start >= session.wall:
                    return "time_limit"
                if ready and now - last >= session.idle:
                    return "idle_timeout"
                if ready and not pipe.closed:
                    with session.lock:
                        pending.extend(session.pending)
                        session.pending.clear()
                        eof = session.eof
                    if eof and not pending:
                        if registered:
                            selector.unregister(pipe)
                            registered = False
                        pipe.close()
                if not pipe.closed:
                    if pending and not registered:
                        selector.register(pipe, selectors.EVENT_WRITE, "stdin")
                        registered = True
                    elif not pending and registered:
                        selector.unregister(pipe)
                        registered = False
                if process.poll() is not None and read_pipes == 0:
                    return None if ready else "judge_error"
                for key, _ in selector.select(0.05):
                    name = key.data
                    if name == "stdin":
                        try:
                            size = os.write(pipe.fileno(), pending[:8192])
                            del pending[:size]
                            last = time.monotonic()
                        except BlockingIOError:
                            continue
                        except BrokenPipeError:
                            selector.unregister(pipe)
                            registered = False
                            pipe.close()
                            pending.clear()
                        continue
                    try:
                        chunk = os.read(key.fileobj.fileno(), 4096)
                    except BlockingIOError:
                        continue
                    if not chunk:
                        selector.unregister(key.fileobj)
                        read_pipes -= 1
                        continue
                    if name == "stderr" and not ready:
                        need = len(ready_marker) - len(prefix)
                        prefix.extend(chunk[:need])
                        if not ready_marker.startswith(prefix):
                            return "judge_error"
                        if len(prefix) != len(ready_marker):
                            continue
                        chunk = chunk[need:]
                        ready = True
                        start = last = time.monotonic()
                        session.ready()
                    if chunk:
                        last = time.monotonic()
                        if not session.append(name, chunk):
                            return "resource_limit"
    finally:
        terminate_group(process)
        for stream in (process.stdin, process.stdout, process.stderr):
            if not stream.closed:
                stream.close()


class Manager:
    def __init__(self, backend, *, idle=30, wall=90):
        self.backend, self.idle, self.wall = backend, idle, wall
        self.lock = threading.Lock()
        self.sessions, self.threads = {}, {}
        self.closed = self.failed = False

    def run(self, session):
        try:
            result = self.backend(session)
        except Exception:
            # Unexpected infrastructure/cleanup errors disable the worker.
            with self.lock:
                self.failed = True
                for other in self.sessions.values():
                    if other is not session:
                        other.cancel.set()
            result = {"status": "judge_error"}
        session.finish(result)

    def request(self, packet):
        owner, task, action = packet["owner"], packet["taskId"], packet["action"]
        if action == "start":
            with self.lock:
                now = time.monotonic()
                for sid, s in list(self.sessions.items()):
                    if s.finished is not None and now - s.finished > 120:
                        self.sessions.pop(sid)
                        self.threads.pop(sid, None)
                if self.closed or self.failed:
                    return {"status": "judge_error"}
                active = [s for s in self.sessions.values() if s.finished is None]
                if len(active) >= 2 or any(s.owner == owner for s in active):
                    return {"status": "busy", "error": "Execution slots occupied; stop or finish the previous run."}
                done = sorted((s for s in self.sessions.values() if s.finished is not None),
                              key=lambda s: s.finished)
                while len(self.sessions) >= 32 and done:
                    expired = done.pop(0)
                    self.sessions.pop(expired.id)
                    self.threads.pop(expired.id, None)
                session = Session(owner, task, packet["code"], self.idle, self.wall)
                self.sessions[session.id] = session
                thread = threading.Thread(target=self.run, args=(session,))
                self.threads[session.id] = thread
                thread.start()
            return session.snapshot()
        with self.lock:
            session = self.sessions.get(packet["sessionId"])
            if (session is None or session.owner != owner or session.task != task or
                    (session.finished is not None and time.monotonic() - session.finished > 120)):
                return {"status": "not_found", "error": "Execution session unavailable."}
        return session.action(action, packet.get("input", ""))

    def close(self):
        with self.lock:
            self.closed = True
            sessions, threads = list(self.sessions.values()), list(self.threads.values())
        for session in sessions:
            session.cancel.set()
        for thread in threads:
            thread.join(timeout=40)
            if thread.is_alive():
                raise RuntimeError("Interactive execution failed to stop")


def valid_packet(packet):
    if not isinstance(packet, dict) or packet.get("version") != 1:
        return False
    def hex_id(value):
        return isinstance(value, str) and len(value) == 32 and all(c in "0123456789abcdef" for c in value)
    owner = packet.get("owner")
    if not isinstance(owner, str) or len(owner) != 65 or owner[32] != ":":
        return False
    if not hex_id(owner[:32]) or not hex_id(owner[33:]) or not hex_id(packet.get("taskId")):
        return False
    action = packet.get("action")
    if action == "start":
        code = packet.get("code")
        return isinstance(code, str) and 0 < len(code.encode()) <= 65536
    if action not in ("poll", "input", "eof", "stop") or not hex_id(packet.get("sessionId")):
        return False
    if action == "input":
        data = packet.get("input")
        return isinstance(data, str) and 0 < len(data.encode()) <= INPUT
    return True
