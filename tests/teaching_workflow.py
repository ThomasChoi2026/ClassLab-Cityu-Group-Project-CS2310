"""Exercise the bundled C++ example and the teacher-only feedback API."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from workflow import request, server

COMPILER = sys.argv.pop(1)
NOTEBOOK = Path(__file__).resolve().parents[1] / "examples/polymorphism-slicing.ipynb"
STARTER = "\n\n".join("".join(cell["source"]).rstrip()
                      for cell in json.loads(NOTEBOOK.read_text())["cells"] if cell["cell_type"] == "code")
FIXED = STARTER.replace("const Animal animal", "const Animal& animal")
CASES = [
    {"name": "Base dispatch", "visibility": "public", "input": "0", "expectedOutput": "animal"},
    {"name": "CHECK_DERIVED_PRIVATELY", "visibility": "hidden", "input": "1", "expectedOutput": "meow"},
]
PITFALL = {"name": "Object slicing", "note": "LOOK_FOR_PASS_BY_VALUE", "needle": "const Animal animal",
           "testNumber": "2"}


class TeachingWorkflow(unittest.TestCase):
    def test_notebook_example_runs_with_real_cpp20(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "exercise"
            for code, expected in [(STARTER, ["animal", "animal"]), (FIXED, ["animal", "meow"])]:
                subprocess.run([COMPILER, "-std=c++20", "-Wall", "-Wextra", "-x", "c++", "-", "-o", str(binary)],
                               input=code, text=True, check=True, timeout=20)
                for kind, word in enumerate(expected):
                    actual = subprocess.run([str(binary)], input=f"{kind}\n", capture_output=True,
                                            text=True, check=True, timeout=3)
                    self.assertEqual(actual.stdout, word + "\n")
            invalid = FIXED.replace("voice() const override", "voice() override")
            result = subprocess.run([COMPILER, "-std=c++20", "-x", "c++", "-fsyntax-only", "-"],
                                    input=invalid, capture_output=True, text=True, timeout=20)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("override", result.stderr)

    def test_teacher_only_evidence_for_latest_submission(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "classrooms.json"
            with server(data) as base:
                _, room = request(base, "/api/rooms", {"name": "Virtual dispatch"})
                path = "/api/rooms/" + room["id"]
                teacher = {"X-Teacher-Key": room["teacherKey"]}
                lesson = {"title": "Object slicing", "description": "Preserve the dynamic type.",
                          "starterCode": STARTER, "testCases": CASES, "pitfalls": [PITFALL]}
                bad = {"pitfalls": [dict(PITFALL, testNumber="3")]}
                self.assertEqual(request(base, path + "/tasks", dict(lesson, **bad), **teacher)[0], 400)
                status, task = request(base, path + "/tasks", lesson, **teacher)
                self.assertEqual(status, 201)
                for name, codes in [("A", [STARTER, FIXED]), ("B", [STARTER])]:
                    _, student = request(base, path + "/students", {"name": name})
                    headers = {"X-Student-Key": student["studentKey"]}
                    for code in codes:
                        receipt = request(base, path + "/submissions", {"taskId": task["id"], "code": code}, **headers)
                        self.assertEqual(receipt[1]["judgement"], "judge_unavailable")
                    student_view = request(base, path + "/task", **headers)[1]
                    self.assertNotIn("pitfalls", student_view["task"])
                    self.assertNotIn("LOOK_FOR_PASS_BY_VALUE", json.dumps(student_view))
                    self.assertNotIn("CHECK_DERIVED_PRIVATELY", json.dumps(student_view))
                    self.assertEqual(request(base, path + "/progress", **headers)[0], 403)
                status, progress = request(base, path + "/progress", **teacher)
                self.assertEqual(status, 200)
                evidence = progress["pitfallStats"][0]
                self.assertEqual((evidence["sourceMatches"], evidence["testObserved"], evidence["testFailures"]),
                                 (1, 0, 0))

            # Feed stored outcome fixtures to validate the dashboard's test counting and recovery separately.
            saved = json.loads(data.read_text())
            for student in saved[room["id"]]["students"].values():
                result = "passed" if student["name"] == "A" else "wrong_answer"
                student["submissions"][-1]["judgement"] = {
                    "status": "accepted" if result == "passed" else "wrong_answer",
                    "cases": [{"testId": "2", "status": result}],
                }
            data.write_text(json.dumps(saved))
            with server(data) as base:
                evidence = request(base, path + "/progress", **teacher)[1]["pitfallStats"][0]
                self.assertEqual((evidence["sourceMatches"], evidence["testObserved"], evidence["testFailures"]),
                                 (1, 2, 1))


if __name__ == "__main__":
    unittest.main()
