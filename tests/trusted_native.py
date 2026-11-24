"""Real GCC integration test, using repository-authored and fixed reviewed test source only."""
import sys
import shutil
import tempfile
from pathlib import Path

from workflow import request, server
from judge_protocol import wait_for

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "judge"))
from trusted_native import NativeEvaluator, approved_sources, native_socket

ADD = "#include <iostream>\nint main(){int a,b; std::cin>>a>>b; std::cout<<a+b<<'\\n';}"
BAD = "#include <iostream>\nint main(){std::cout<<1}"
WRONG = ADD.replace("a+b", "a-b")
HELLO = "#include <iostream>\nint main(){std::cout<<\"Hello\\n\";}"

def main():
    compiler = shutil.which("g++")
    assert compiler and Path("/usr/bin/prlimit").exists()
    sources = approved_sources()
    assert len(sources) >= 32
    sources.update({code: code for code in (ADD, BAD, WRONG, HELLO)})
    evaluator = NativeEvaluator(compiler, sources)
    assert evaluator(ADD, [""], "probe")["status"] == "stdin_required"
    result = evaluator(ADD, ["15 27"], "run")
    assert bytes.fromhex(result["cases"][0]["stdoutHex"]) == b"42\n"
    assert evaluator(BAD, [""], "run")["status"] == "compilation_error"
    assert evaluator(HELLO, [""], "probe")["cases"][0]["status"] == "success"
    assert evaluator(HELLO + "\n// not approved", [""], "run")["status"] == "source_not_approved"
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)
        socket = path / "judge.sock"
        with native_socket(socket, evaluator), server(path / "data.json", socket) as base:
            _, room = request(base, "/api/rooms", {"name": "Native test"})
            root = "/api/rooms/" + room["id"]
            teacher = {"X-Teacher-Key": room["teacherKey"]}
            _, task = request(base, root + "/tasks", {"title": "Add", "starterCode": ADD,
                "testCases": [{"name": "Public", "input": "15 27", "expectedOutput": "42", "visibility": "public"},
                              {"name": "Private", "input": "2 7", "expectedOutput": "9", "visibility": "hidden"}]}, **teacher)
            for i, (code, expected) in enumerate(((ADD, "accepted"), (WRONG, "wrong_answer"),
                                                  (BAD, "compilation_error"), (HELLO + "// not approved", "source_not_approved"))):
                _, student = request(base, root + "/students", {"name": str(i)})
                headers = {"X-Student-Key": student["studentKey"]}
                status, result = request(base, root + "/submissions", {"taskId": task["id"], "code": code}, **headers)
                assert status == 201, result
                state = wait_for(lambda: request(base, root + "/task", **headers)[1],
                    lambda view: view["latestResult"] and view["latestResult"]["status"] == expected, timeout=60)
                assert "Private" not in str(state), state
            _, progress = request(base, root + "/progress", **teacher)
            assert (progress["submitted"], progress["accepted"], progress["failed"], progress["unjudged"]) == (4, 1, 2, 1), progress
    print("Trusted native GCC: genuine execution, stdin, compile errors, grading, rejected unapproved source.")

if __name__ == "__main__":
    main()
