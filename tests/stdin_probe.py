"""Native Run-first stdin probe with fixed, trusted C++20 fixtures.

This deliberately executes ONLY hard-coded test programs on the host.
It does not run student submissions or certify the Docker/gVisor sandbox.
"""
import base64
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "judge"))
import worker


class StdinProbe(unittest.TestCase):
    compiler = sys.argv.pop(1) if len(sys.argv) > 1 else "g++"

    def run_trusted(self, source, *, probe=True, input_text=""):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            code = directory / "trusted.cpp"
            binary = directory / "trusted-program"
            code.write_text(source)
            subprocess.run([self.compiler, "-std=c++20", "-O0", str(code),
                            "-o", str(binary)], check=True, timeout=30)
            script = (worker.EXECUTE_PROBE if probe else worker.EXECUTE)
            script = script.replace("/work/", str(directory) + "/")
            stdin = base64.b64encode(binary.read_bytes()) + b"\n"
            if not probe:
                stdin += input_text.encode()
            return subprocess.run(["/bin/bash", "-c", script], input=stdin,
                                  capture_output=True, timeout=10)

    def assert_needs_input(self, source):
        result = self.run_trusted(source)
        self.assertEqual(result.returncode, worker.STDIN_PROBE_EXIT,
                         (result.stdout, result.stderr))
        self.assertTrue(result.stderr.endswith(worker.STDIN_PROBE_MARKER))
        self.assertIn(worker.READY, result.stderr)

    def test_no_input_runs_normally(self):
        source = '#include <iostream>\nint main(){std::cout<<"Hello\\n";}'
        result = self.run_trusted(source)
        self.assertEqual((result.returncode, result.stdout), (0, b"Hello\n"))
        self.assertNotIn(worker.STDIN_PROBE_MARKER, result.stderr)

    def test_cin_triggers_only_after_actual_read(self):
        self.assert_needs_input(
            '#include <iostream>\nint main(){int n;std::cout<<"Enter: "<<std::flush;'
            'std::cin>>n;std::cout<<n;}')

    def test_getline_triggers(self):
        self.assert_needs_input(
            '#include <iostream>\n#include <string>\nint main(){std::string s;'
            'std::getline(std::cin,s);std::cout<<s;}')

    def test_scanf_triggers(self):
        self.assert_needs_input(
            '#include <cstdio>\nint main(){int n;scanf("%d",&n);printf("%d",n);}')

    def test_posix_read_triggers(self):
        self.assert_needs_input(
            '#include <unistd.h>\nint main(){char c;return read(0,&c,1)<0;}')

    def test_input_is_applied_on_fresh_real_run(self):
        source = '#include <iostream>\nint main(){int n;std::cin>>n;std::cout<<"RESULT="<<n<<"\\n";}'
        result = self.run_trusted(source, probe=False, input_text="17\n")
        self.assertEqual((result.returncode, result.stdout), (0, b"RESULT=17\n"))

    def test_nonzero_without_stdin_remains_runtime_error(self):
        result = self.run_trusted('int main(){return 7;}')
        self.assertEqual(result.returncode, 7)
        self.assertNotIn(worker.STDIN_PROBE_MARKER, result.stderr)


if __name__ == "__main__":
    unittest.main()
