"""Test the worker's stream supervisor with bounded, trusted helper processes."""
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from judge import worker


class Supervisor(unittest.TestCase):
    @staticmethod
    def collect(code, timeout=2, cap=1024):
        with subprocess.Popen([sys.executable, "-c", code], stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
            try:
                return worker.collect(proc, b"", timeout, cap, expect_ready=True)
            finally:
                if proc.poll() is None:
                    proc.kill()

    def test_boot_failure_is_not_student_timeout(self):
        self.assertEqual(self.collect("print('container failed', file=__import__('sys').stderr)")[0], "judge_error")
        with patch.object(worker, "BOOT_TIMEOUT", 0.1):
            self.assertEqual(self.collect("import time; time.sleep(0.6)")[0], "judge_error")

    def test_program_deadline_and_output_cap(self):
        marker = repr(worker.READY)
        self.assertEqual(self.collect(f"import os,time; os.write(2,{marker}); time.sleep(0.6)", timeout=0.1)[0],
                         "time_limit")
        status, buffers = self.collect(f"import os; os.write(2,{marker}); os.write(1,b'0123456789')", cap=4)
        self.assertEqual((status, bytes(buffers["stdout"])), ("resource_limit", b"0123"))

    def test_boot_marker_is_not_shown_in_program_stderr(self):
        marker = repr(worker.READY)
        status, buffers = self.collect(f"import os; boot={marker}; os.write(2,boot[:3]); "
                                       "os.write(2,boot[3:]+b'diagnostic'); os.write(1,b'8')")
        self.assertIsNone(status)
        self.assertEqual((bytes(buffers["stdout"]), bytes(buffers["stderr"])), (b"8", b"diagnostic"))


if __name__ == "__main__":
    unittest.main()
