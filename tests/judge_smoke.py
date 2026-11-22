"""Real container compilation with fixed, trusted examples only."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from judge import worker

INCLUDE = "#include <iostream>\n"
ADD = INCLUDE + "int main(){int a,b; std::cin>>a>>b; std::cout<<a+b<<'\\n';}"
SUBTRACT = INCLUDE + "int main(){int a,b; std::cin>>a>>b; std::cout<<a-b<<'\\n';}"
SEMICOLON = "int main(){int x=10\nreturn 0;}"
MISSING = "int main(){return missing;}"
HELLO = INCLUDE + 'int main(){std::cout<<"Hello World\\n";}'
NONZERO = INCLUDE + 'int main(){std::cerr<<"example"; return 7;}'


def outputs(source, inputs, expected):
    result = worker.evaluate(source, inputs, "run")
    assert result["status"] == "success", result
    assert [(entry["status"], bytes.fromhex(entry["stdoutHex"]).decode()) for entry in result["cases"]] == [
        ("success", text) for text in expected], result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", choices=("runsc", "runc"), default=worker.RUNTIME)
    parser.add_argument("--acceptance", action="store_true",
                        help="test enforced limits only after the runtime preflight passes")
    args = parser.parse_args()
    worker.RUNTIME = args.runtime
    if not Path(worker.DOCKER[0]).is_file():
        worker.DOCKER[0] = "/usr/bin/docker"
    if args.acceptance:
        worker.verify_runtime()

    outputs(HELLO, [""], ["Hello World\n"])
    outputs(ADD, ["5 3", "2 3", "0 0", "-4 9"], ["8\n", "5\n", "0\n", "5\n"])
    outputs(SUBTRACT, ["2 3", "0 0"], ["-1\n", "0\n"])
    for source, diagnostic in [(SEMICOLON, "expected"), (MISSING, "not declared")]:
        result = worker.evaluate(source, [""], "run")
        assert result["status"] == "compilation_error" and diagnostic in result["diagnostic"], result
    result = worker.evaluate(NONZERO, [""], "run")["cases"][0]
    assert (result["status"], result["exitCode"], result["stderr"]) == ("runtime_error", 7, "example"), result
    print("Real GCC smoke: Hello World, stdin/stdout, wrong answer output, two diagnostics, exit 7.")

    if args.acceptance:
        failure, _, _ = worker.sandbox("exec sleep 5", b"", 0.5, worker.OUTPUT)
        assert failure == "time_limit", "the compiler-stage supervisor did not enforce a wall deadline"
        for source, expected in [
            ("int main(){volatile int n=0; for(;;) n=0;}", "time_limit"),
            (INCLUDE + 'int main(){ for(int i=0;i<20000;++i) std::cout<<"1234567890"; }', "resource_limit"),
            ("#include <csignal>\nint main(){std::raise(SIGSEGV);}", "runtime_error"),
            ("#include <vector>\nint main(){std::vector<unsigned char> data(380UL*1024*1024,7);"
             "return data.back();}", "resource_limit"),
        ]:
            result = worker.evaluate(source, [""], "run")
            assert result["cases"][0]["status"] == expected, result
        process_probe = """#include <cstdio>
#include <csignal>
#include <sys/wait.h>
#include <unistd.h>
int main() {
    int pids[40], count = 0;
    for (; count < 40; ++count) {
        int pid = fork();
        if (pid < 0) break;
        if (pid == 0) { pause(); _exit(0); }
        pids[count] = pid;
    }
    for (int i = 0; i < count; ++i) kill(pids[i], SIGKILL);
    for (int i = 0; i < count; ++i) waitpid(pids[i], nullptr, 0);
    return (count > 0 && count < 32) ? 0 : 1;
}
"""
        outputs(process_probe, [""], [""])
        ids = worker.docker("ps", "-aq", "--filter", "label=" + worker.OWNER_LABEL).strip()
        assert not ids, "judge containers still present after the checks"
        print("Runtime acceptance: wall deadlines, output, memory, PIDs, signals and cleanup passed.")


if __name__ == "__main__":
    main()
