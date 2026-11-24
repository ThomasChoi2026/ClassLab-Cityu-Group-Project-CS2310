"""Full real-Chromium classroom workflow with the new authored Notebook and safe fixture playback."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
LECTURE = ROOT / "examples/CS2310_Score_Analysis.ipynb"


def student_state(page):
    return page.evaluate("""async () => {
        const room = location.pathname.split("/").pop();
        const key = localStorage.getItem("classlab.student." + room);
        const response = await fetch("/api/rooms/" + room + "/task", {headers: {"X-Student-Key": key}});
        if (!response.ok) throw new Error("Student state failed");
        return response.json();
    }""")


def check(browser, base, evidence):
    notebook = json.loads(LECTURE.read_text(encoding="utf-8"))
    references = json.loads((ROOT / "examples/score_analysis_references.json").read_text(encoding="utf-8"))
    title = "Fix the grade boundary"
    ref = references[title]
    first = notebook["cells"][ref["cell"] - 1]
    metadata = first["metadata"]["classlab"]
    starter = first["source"].removeprefix("%%cpp\n")
    public = [{"name": t["name"], "input": t["input"], "expectedOutput": t["expectedOutput"]}
              for t in metadata["testCases"] if t["visibility"] == "public"]
    evidence.mkdir(parents=True, exist_ok=True)
    errors = []
    teacher = browser.new_page(viewport={"width": 1440, "height": 1080})
    teacher.on("pageerror", lambda error: errors.append(str(error)))
    teacher.goto(base)
    expect(teacher.locator("#demo-banner")).to_be_visible()
    teacher.locator("#create input").fill("CS2310 Score Analysis")
    teacher.get_by_role("button", name="创建课堂", exact=True).click()
    expect(teacher.locator("#current-task")).to_have_text("尚未发布任务")
    teacher.locator("#compose-prep").click()
    upload = teacher.locator("#notebook-file")
    expect(upload).to_be_visible()
    expect(teacher.locator("#notebook-cells")).to_be_hidden()
    teacher.locator("[name=title]").fill("Preserve this draft")
    teacher.locator("[name=starterCode]").fill("int main() { return 7; }")
    upload.set_input_files(LECTURE)
    expect(teacher.locator("#notebook-overview")).to_contain_text("CS2310_Score_Analysis.ipynb")
    expect(teacher.locator("#notebook-overview")).to_contain_text("总 Cell：74")
    expect(teacher.locator("#notebook-overview")).to_contain_text("课堂互动练习：5")
    expect(teacher.locator("#notebook-filter")).to_have_value("exercise")
    expect(teacher.locator("#notebook-list button")).to_have_count(5)
    assert teacher.locator("[name=title]").input_value() == "Preserve this draft"
    expect(teacher.locator("#current-task")).to_have_text("尚未发布任务")
    teacher.locator("#notebook-search").fill("Find the maximum correctly")
    expect(teacher.locator("#notebook-list button")).to_have_count(1)
    expect(teacher.locator("#notebook-list button").first).to_contain_text("Cell 48")
    teacher.locator("#notebook-search").fill("")
    exercise = teacher.locator("#notebook-list button").filter(has_text=title)
    teacher.once("dialog", lambda dialog: dialog.dismiss())
    exercise.click()
    expect(teacher.locator("[name=title]")).to_have_value("Preserve this draft")
    expect(teacher.locator("[name=starterCode]")).to_have_value("int main() { return 7; }")
    teacher.once("dialog", lambda dialog: dialog.accept())
    teacher.locator("#use-notebook-cell").click()
    expect(teacher.locator("[name=title]")).to_have_value(title)
    expect(teacher.locator("[name=description]")).to_have_value(metadata["description"])
    expect(teacher.locator("[name=starterCode]")).to_have_value(starter)
    expect(teacher.locator("#case-editor-rows .case-row")).to_have_count(len(metadata["testCases"]))
    expect(teacher.locator("#pitfall-rows .case-row")).to_have_count(1)
    expect(teacher.locator("#case-editor-rows [data-field=visibility]").nth(3)).to_have_value("hidden")
    expect(teacher.locator("#current-task")).to_have_text("尚未发布任务")
    teacher.screenshot(path=str(evidence / "01-marked-notebook-and-loaded-exercise.png"), full_page=True)

    # The teacher reference Markdown is visible to the teacher, never transferable.
    teacher.locator("#notebook-filter").select_option("all")
    teacher.locator("#notebook-list button").filter(has_text="Cell 74 ·").click()
    expect(teacher.locator("#append-notebook-text")).to_be_hidden()
    expect(teacher.locator("#use-notebook-cell")).to_be_hidden()
    expect(teacher.locator("#toggle-prep-cell")).to_be_hidden()
    expect(teacher.locator("[name=starterCode]")).to_have_value(starter)
    teacher.locator("#notebook-filter").select_option("exercise")
    teacher.locator("#publish-task").click()
    expect(teacher.locator("#current-task")).to_contain_text(title)
    expect(teacher.locator("#notebook-list button")).to_have_count(5)
    join = teacher.locator("#join-link").input_value()
    students = []
    for index, change in enumerate((False, True, True), 1):
        student = browser.new_page(viewport={"width": 1000, "height": 950})
        students.append(student)
        student.on("pageerror", lambda error: errors.append(str(error)))
        student.goto(join)
        student.locator("#join input").fill(f"Student {index}")
        student.locator("#join button").click()
        expect(student.locator("#task-title")).to_have_text(title)
        editor = student.locator("#student-code")
        expect(editor).to_have_value(starter)
        expect(student.locator("#task-description")).to_have_text(metadata["description"])
        task = student_state(student)["task"]
        assert set(task) == {"id", "title", "description", "starterCode", "testCases"}
        assert task["testCases"] == public
        assert "pitfalls" not in task and "referenceSource" not in task
        assert student.request.get(base + "/examples/CS2310_Score_Analysis.ipynb").status == 404
        assert student.request.get(base + "/examples/score_analysis_references.json").status == 404
        expect(student.locator("#open-optcpp")).to_have_text("抄送至OPT_CPP")
        assert student.locator("#embedded-optcpp").count() == 0
        if change:
            editor.fill(starter.replace("score > 60", "score >= 60"))
            assert editor.input_value().strip() == ref["referenceSource"].strip()
        expect(student.locator("#stdin-panel")).to_be_hidden()
        expect(student.locator("#run-code")).to_be_enabled()
        student.locator("#run-code").click()
        expect(student.locator("#stdin-panel")).to_be_visible()
        expect(student.locator("#run-result")).to_contain_text("不会执行当前代码")
        expect(student.locator("#stdin-label")).to_have_text("预置演示输入（stdin）")
        student.locator("[name=runInput]").fill("60")
        student.locator("#run-code").click()
        result = student.locator("#run-result")
        expect(result).to_contain_text("预置演示回放")
        expect(result.locator("pre")).to_have_text("PASS" if change else "FAIL")
        expect(student.locator("#stdin-panel")).to_be_hidden()
        if index == 2:
            student.screenshot(path=str(evidence / "02-student-run-replay.png"), full_page=True)
        # Hidden cases and arbitrary source are not executable via the Demo Run endpoint.
        if index == 1:
            student.locator("#run-code").click()
            expect(student.locator("#stdin-panel")).to_be_visible()
            student.locator("[name=runInput]").fill("100")
            student.locator("#run-code").click()
            expect(result).to_contain_text("无匹配")
            expect(result.locator("pre")).to_have_count(0)
            editor.fill(starter + "\n// Unregistered source")
            student.locator("#run-code").click()
            expect(result).to_contain_text("无匹配")
            expect(result.locator("pre")).to_have_count(0)
            editor.fill(starter)
        editor.press("Control+Enter")
        verdict = student.locator("#student-result")
        expect(verdict).to_contain_text("全部通过" if change else "输出不符", timeout=15000)
        expect(verdict).to_contain_text("预置演示回放")
        state = student_state(student)
        hidden = [row for row in state["latestResult"]["cases"] if row["name"].startswith("隐藏测试")]
        assert len(hidden) == 2 and all(set(row) == {"name", "status"} for row in hidden), hidden

    expect(teacher.locator("#submitted")).to_have_text("3", timeout=12000)
    expect(teacher.locator("#accepted")).to_have_text("2")
    expect(teacher.locator("#failed")).to_have_text("1")
    teacher.screenshot(path=str(evidence / "03-live-classroom-statistics.png"), full_page=True)
    patterns = teacher.locator("#edit-patterns")
    expect(patterns).to_contain_text("全部通过 2 人")
    patterns.get_by_role("button").first.click()
    expect(teacher.locator(".diff-del")).to_contain_text("score > 60")
    expect(teacher.locator(".diff-add")).to_contain_text("score >= 60")
    teacher.screenshot(path=str(evidence / "04-common-edit.png"), full_page=True)
    teacher.locator("#submission-dialog").get_by_role("button", name="关闭").click()
    # A second marked exercise can be selected and published without reuploading.
    teacher.locator("#notebook-list button").filter(has_text="Debug the accumulation loop").click()
    expect(teacher.locator("[name=title]")).to_have_value("Debug the accumulation loop")
    expect(teacher.locator("#current-task")).to_contain_text(title)
    teacher.locator("#publish-task").click()
    expect(teacher.locator("#current-task")).to_contain_text("Debug the accumulation loop")
    expect(students[0].locator("#task-title")).to_have_text("Debug the accumulation loop", timeout=10000)
    assert "i < n - 1" in students[0].locator("#student-code").input_value()
    assert not errors, errors
    for student in students:
        student.close()
    teacher.close()
    print("Notebook classroom browser acceptance passed: direct import, 74/5 filter, safe replacement, private metadata, real submissions, labeled replay, analytics, next exercise.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--evidence-dir", type=Path, default=Path("notebook-evidence"))
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            check(browser, args.url, args.evidence_dir)
        finally:
            browser.close()
