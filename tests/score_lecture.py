"""Compile and execute only repository-authored C++ examples. Never execute student input as source."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from demo.run import SCORE_FIXTURES, score_playback

# Expected results independently stated in the lecture or calculated from its example.
NORMAL = {
    3: ("", "78 5 83\n"),
    5: ("", "60 83\n"),
    8: ("71\n", "73\n"),
    11: ("", "80 80.5\n"),
    14: ("", "true\n"),
    16: ("", "FAIL\n"),
    19: ("", "A\n"),
    25: ("", "1: 10\n2: 30\n3: 60\n4: 100\n"),
    27: ("10 20 30\n", "60\n"),
    29: ("10 20 -1\n", "30\n"),
    32: ("60 80 59 1\n", "200 2\n"),
    38: ("", "72 55\n65\n"),
    40: ("", "0: 72\n1: 60\n2: 91\n3: 55\n"),
    42: ("", "223\n"),
    45: ("", "-3\n"),
    51: ("", "false true\n"),
    53: ("", "75 80\n"),
    55: ("", "80\n"),
    58: ("", "231\n"),
    60: ("", "80.50\n"),
    67: ("", "3\n"),
    69: ("", "100\n"),
}


def source_of(cell):
    source = "".join(cell["source"]).strip()
    return source.removeprefix("%%cpp\n").strip()


def compile_program(compiler, directory, label, code):
    source = directory / (label + ".cpp")
    binary = directory / label
    source.write_text(code + "\n", encoding="utf-8")
    subprocess.run([compiler, "-std=c++20", "-pedantic-errors", str(source),
                    "-o", str(binary)], check=True, timeout=30, capture_output=True)
    return binary


def run(binary, stdin):
    result = subprocess.run([str(binary)], input=stdin, text=True,
                            capture_output=True, check=True, timeout=3)
    assert not result.stderr, (binary.name, result.stderr)
    return result.stdout


def main(compiler):
    lecture = json.loads((ROOT / "examples/CS2310_Score_Analysis.ipynb").read_text(encoding="utf-8"))
    references = json.loads((ROOT / "examples/score_analysis_references.json").read_text(encoding="utf-8"))
    exercises = {r["cell"]: (title, r) for title, r in references.items()}
    assert len(lecture["cells"]) == 74 and len(exercises) == 5
    normal_count = checks = 0
    with tempfile.TemporaryDirectory(prefix="classlab-trusted-lecture-") as tmp:
        directory = Path(tmp)
        for index, cell in enumerate(lecture["cells"], 1):
            if cell["cell_type"] != "code":
                continue
            source = source_of(cell)
            starter = compile_program(compiler, directory, f"cell{index}", source)
            if index not in exercises:
                stdin, output = NORMAL[index]
                assert run(starter, stdin) == output, (index, "ordinary teaching example")
                normal_count += 1
                continue
            title, reference = exercises[index]
            meta = cell["metadata"]["classlab"]
            assert source.startswith("// @classlab exercise: " + title + "\n")
            answer = reference["referenceSource"].strip()
            assert source != answer
            corrected = compile_program(compiler, directory, f"reference{index}", answer)
            cases = meta["testCases"]
            inputs = [case["input"] for case in cases]
            observed = []
            for case in cases:
                actual_starter = run(starter, case["input"])
                actual_reference = run(corrected, case["input"])
                observed.append(actual_starter)
                assert actual_reference == case["expectedOutput"], (title, case["name"], actual_reference)
                for fixture_source, actual in [(source, actual_starter), (answer, actual_reference)]:
                    fixture = SCORE_FIXTURES[fixture_source]
                    replay = score_playback(fixture, "run", [case["input"]])
                    if case["visibility"] == "hidden":
                        assert replay["status"] == "demo_no_fixture"
                    else:
                        assert bytes.fromhex(replay["cases"][0]["stdoutHex"]).decode() == actual
                checks += 1
            assert observed == reference["starterOutputs"], (title, observed)
            assert any(a != b["expectedOutput"] for a, b in zip(observed, cases)), title
            assert any(a != b["expectedOutput"] and b["visibility"] == "public" for a,b in zip(observed,cases)), title
            for fixture_source, expected in [(source, observed), (answer, [c["expectedOutput"] for c in cases])]:
                fixture = SCORE_FIXTURES[fixture_source]
                assert score_playback(fixture, "probe", [""])["status"] == "stdin_required"
                results = score_playback(fixture, "grade", inputs)
                assert [bytes.fromhex(c["stdoutHex"]).decode() for c in results["cases"]] == expected
                assert score_playback(fixture, "grade", inputs[:-1])["status"] == "demo_no_fixture"
                assert score_playback(fixture, "run", ["unregistered"])["status"] == "demo_no_fixture"
            assert source + "\n// modified student code" not in SCORE_FIXTURES
            print(f"Cell {index}: {title}: {len(cases)} validated tests; starter defect reproduced")
    assert normal_count == len(NORMAL)
    print(f"Verified {normal_count} normal programs + 5 starters + 5 references; {checks} exercise cases for each variant.")


if __name__ == "__main__":
    main(sys.argv[1])
