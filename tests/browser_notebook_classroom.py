"""Full Chromium classroom workflow with the authored Notebook and no Judge."""
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


def check_notebook_layout(page, evidence, label):
    # Test actual container widths rather than the full viewport alone.
    result = page.evaluate("""() => {
        const browser = document.querySelector(".notebook-browser");
        const list = document.querySelector("#notebook-list");
        const preview = document.querySelector("#notebook-preview");
        const container = document.querySelector("#notebook-import");
        const cs = getComputedStyle(container);
        const contentWidth = container.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
        const columns = getComputedStyle(browser).gridTemplateColumns.split(" ").map(parseFloat);
        const buttons = [...list.querySelectorAll("button")];
        const failures = [];
        let previous = null;
        for (const button of buttons) {
            const rect = button.getBoundingClientRect();
            if (previous && rect.top < previous.bottom - 1) failures.push("overlapping rows");
            previous = rect;
            if (button.scrollWidth > button.clientWidth + 1 || button.scrollHeight > button.clientHeight + 1)
                failures.push("clipped button: " + button.textContent);
            for (const part of button.querySelectorAll("span")) {
                const box = part.getBoundingClientRect();
                if (box.left < rect.left - 1 || box.right > rect.right + 1 ||
                    box.top < rect.top - 1 || box.bottom > rect.bottom + 1 ||
                    part.scrollWidth > part.clientWidth + 1)
                    failures.push("clipped text: " + part.textContent);
            }
            if (button.querySelector(".notebook-cell-meta").textContent.includes("Interactive exercise"))
                failures.push("repeated classification");
        }
        if (list.scrollWidth > list.clientWidth + 1) failures.push("horizontal list overflow");
        if (browser.scrollWidth > browser.clientWidth + 1) failures.push("horizontal container overflow");
        const split = contentWidth >= 41 * parseFloat(getComputedStyle(document.documentElement).fontSize);
        if (columns.length !== (split ? 2 : 1)) failures.push("wrong column count for container");
        if (!split && preview.getBoundingClientRect().width < browser.clientWidth - 2)
            failures.push("stacked preview too narrow");
        if (split && columns[1] < 22 * parseFloat(getComputedStyle(document.documentElement).fontSize) - 1)
            failures.push("split preview too narrow");
        if (getComputedStyle(preview).whiteSpace !== "pre" || getComputedStyle(preview).overflowX !== "auto")
            failures.push("preview does not preserve source or scroll independently");
        return {failures, contentWidth, columns, count: buttons.length,
            titles: buttons.map(b => b.querySelector(".notebook-cell-title").textContent)};
    }""")
    assert result["count"] == 5, (label, result)
    assert not result["failures"], (label, result)
    page.locator("#notebook-import").screenshot(path=str(evidence / f"ux-notebook-{label}.png"))
    return result["titles"]


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
    # The standalone preparation composer can be much wider than the
    # half-width classroom composer. Exercise both sides of the query.
    preparation = browser.new_page(viewport={"width": 1440, "height": 1080})
    preparation.goto(base)
    preparation.locator("#open-preparation").click()
    preparation.locator("#notebook-file").set_input_files(LECTURE)
    expect(preparation.locator("#notebook-list button")).to_have_count(5)
    assert set(check_notebook_layout(preparation, evidence, "preparation-wide")) == set(references)
    preparation.set_viewport_size({"width": 780, "height": 960})
    assert set(check_notebook_layout(preparation, evidence, "preparation-split")) == set(references)
    preparation.close()
    errors = []
    teacher = browser.new_page(viewport={"width": 1440, "height": 1080})
    teacher.on("pageerror", lambda error: errors.append(str(error)))
    teacher.goto(base)
    expect(teacher.locator("#demo-cases")).to_have_count(0)
    teacher.locator("#open-teacher-guide").click()
    guide = teacher.locator("#teacher-guide")
    expect(guide).to_be_visible()
    for phrase in ("CS2310_Score_Analysis.ipynb", "Publish as current task", "View published tasks", "@classlab exercise", "judge"):
        expect(guide).to_contain_text(phrase)
    guide.get_by_role("button", name="Close").click()
    expect(guide).to_be_hidden()
    teacher.locator("#create input").fill("CS2310 Score Analysis")
    teacher.get_by_role("button", name="Create classroom", exact=True).click()
    expect(teacher.locator("#current-task")).to_have_text("No task published yet")
    expect(teacher.locator("#compose-prep")).to_have_attribute("aria-pressed", "true")
    expect(teacher.locator("#notebook-file")).to_be_visible()
    teacher.locator("#compose-quick").click()
    expect(teacher.locator("#notebook-import")).to_be_hidden()
    teacher.locator("[name=title]").fill("Quick draft stays")
    teacher.locator("#compose-prep").click()
    expect(teacher.locator("[name=title]")).to_have_value("")
    teacher.locator("#compose-quick").click()
    expect(teacher.locator("[name=title]")).to_have_value("Quick draft stays")
    teacher.locator("#compose-prep").click()
    upload = teacher.locator("#notebook-file")
    expect(upload).to_be_visible()
    expect(teacher.locator("#normal-notebook-download")).to_be_visible()
    expect(teacher.locator("#notebook-cells")).to_be_hidden()
    teacher.locator("[name=title]").fill("Preserve this draft")
    teacher.locator("[name=starterCode]").fill("int main() { return 7; }")
    upload.set_input_files(LECTURE)
    expect(teacher.locator("#notebook-overview")).to_contain_text("CS2310_Score_Analysis.ipynb")
    expect(teacher.locator("#notebook-overview")).to_contain_text("Total cells: 74")
    expect(teacher.locator("#notebook-overview")).to_contain_text("Interactive exercises: 5")
    expect(teacher.locator("#notebook-filter")).to_have_value("exercise")
    expect(teacher.locator("#notebook-list button")).to_have_count(5)
    for width in (1440, 1280, 1100, 960, 860, 768, 600, 390):
        teacher.set_viewport_size({"width": width, "height": 1080})
        assert set(check_notebook_layout(teacher, evidence, str(width))) == set(references)
    # Desktop zoom reduces the available layout viewport. These are equivalent
    # CSS viewport widths for 125% and 150% at 1440 physical pixels, not a
    # claim that Chromium's browser-chrome zoom control was exercised.
    for zoom in (1.25, 1.5):
        teacher.set_viewport_size({"width": round(1440 / zoom), "height": round(1080 / zoom)})
        check_notebook_layout(teacher, evidence, f"effective-{int(zoom * 100)}pct")
    teacher.set_viewport_size({"width": 1440, "height": 1080})
    assert teacher.locator("[name=title]").input_value() == "Preserve this draft"
    expect(teacher.locator("#current-task")).to_have_text("No task published yet")
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
    expect(teacher.locator("#preparation-counts")).to_have_text("Test cases: 5 · Pitfalls: 1")
    expect(teacher.locator("#teacher-optional-settings")).not_to_have_attribute("open", "")
    expect(teacher.locator("#prep-library")).not_to_have_attribute("open", "")
    expect(teacher.locator("#notebook-combination")).to_be_hidden()
    expect(teacher.locator("#case-editor-rows [data-field=visibility]").nth(3)).to_have_value("hidden")
    expect(teacher.locator("#current-task")).to_have_text("No task published yet")
    teacher.screenshot(path=str(evidence / "01-marked-notebook-and-loaded-exercise.png"), full_page=True)

    # The teacher reference Markdown is visible to the teacher, never transferable.
    teacher.locator("#notebook-filter").select_option("all")
    teacher.locator("#notebook-list button").filter(has_text="Cell 74 ·").click()
    expect(teacher.locator("#append-notebook-text")).to_be_hidden()
    expect(teacher.locator("#use-notebook-cell")).to_be_hidden()
    expect(teacher.locator("#toggle-prep-cell")).to_be_hidden()
    expect(teacher.locator("[name=starterCode]")).to_have_value(starter)
    def publish_marked(name, code, fields):
        row_selector = "#case-editor-rows .case-row"
        teacher_cases = teacher.locator(row_selector).evaluate_all("""rows => rows.map(row =>
            Object.fromEntries([...row.querySelectorAll("[data-field]")].map(field =>
                [field.dataset.field, field.value])))""")
        assert teacher_cases == fields["testCases"], name
        with teacher.expect_response(lambda response: response.request.method == "POST"
                                      and response.url.endswith("/tasks")) as published:
            teacher.locator("#publish-task").click()
        assert published.value.status == 201, published.value.text()
        task = published.value.json()
        assert (task["title"], task["starterCode"], task["description"]) == (name, code, fields["description"])
        assert [{key: value for key, value in case.items() if key != "id"}
                for case in task["testCases"]] == fields["testCases"], name

        expect(teacher.locator("#current-task")).to_contain_text(name)
        for field in ("title", "description", "starterCode"):
            expect(teacher.locator(f"[name={field}]")).to_have_value("")
        expect(teacher.locator(row_selector)).to_have_count(0)
        expect(teacher.locator("#pitfall-rows .case-row")).to_have_count(0)
        expect(teacher.locator("#preparation-counts")).to_have_text("Test cases: 0 · Pitfalls: 0")
        expect(teacher.locator("#notebook-list button")).to_have_count(5)
        return task["id"]

    teacher.locator("#notebook-filter").select_option("exercise")
    first_task_id = publish_marked(title, starter, metadata)
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
        expect(student.locator("#open-optcpp")).to_have_text("Send to OPT CPP")
        assert student.locator("#embedded-optcpp").count() == 0
        if change:
            editor.fill(starter.replace("score > 60", "score >= 60"))
            assert editor.input_value().strip() == ref["referenceSource"].strip()
        expect(student.locator("#stdin-panel")).to_be_hidden()
        expect(student.locator("#run-code")).to_be_disabled()
        editor.press("Control+Enter")
        verdict = student.locator("#student-result")
        expect(verdict).to_contain_text("Ungraded")
        state = student_state(student)
        assert state["latestResult"]["status"] == "judge_unavailable", state
        assert not state["latestResult"].get("cases"), state

    expect(teacher.locator("#submitted")).to_have_text("3", timeout=12000)
    expect(teacher.locator("#accepted")).to_have_text("0")
    expect(teacher.locator("#failed")).to_have_text("0")
    teacher.screenshot(path=str(evidence / "03-live-classroom-statistics.png"), full_page=True)
    patterns = teacher.locator("#edit-patterns")
    expect(patterns).to_contain_text("score > 60")
    patterns.get_by_role("button").first.click()
    expect(teacher.locator(".diff-del")).to_contain_text("score > 60")
    expect(teacher.locator(".diff-add")).to_contain_text("score >= 60")
    teacher.screenshot(path=str(evidence / "04-common-edit.png"), full_page=True)
    teacher.locator("#submission-dialog").get_by_role("button", name="Close").click()
    # Publish all five marked exercises from the original import for an already joined student.
    assert len(references) == 5
    last_title = title
    for next_title, next_ref in references.items():
        if next_title == title:
            continue
        cell = notebook["cells"][next_ref["cell"] - 1]
        code = cell["source"].removeprefix("%%cpp\n")
        fields = cell["metadata"]["classlab"]
        student = students[0]
        student.locator("#student-code").fill("// prior task draft")
        teacher.locator("#notebook-list button").filter(has_text=next_title).click()
        expect(teacher.locator("[name=title]")).to_have_value(next_title)
        expect(teacher.locator("[name=starterCode]")).to_have_value(code)
        expect(teacher.locator("[name=description]")).to_have_value(fields["description"])
        expect(teacher.locator("#preparation-counts")).to_have_text(
            f"Test cases: {len(fields['testCases'])} · Pitfalls: {len(fields['pitfalls'])}"
        )
        expect(teacher.locator("#current-task")).to_contain_text(last_title)
        next_task_id = publish_marked(next_title, code, fields)
        expect(student.locator("#task-title")).to_have_text(next_title)
        expect(student.locator("#student-code")).to_have_value(code)
        expect(student.locator("#task-description")).to_have_text(fields["description"])
        task = student_state(student)["task"]
        assert task["testCases"] == [
            {key: case[key] for key in ("name", "input", "expectedOutput")}
            for case in fields["testCases"] if case["visibility"] == "public"
        ], next_title
        assert "pitfalls" not in task, next_title
        if last_title == title:
            # Inspect the first task by its actual ID, while students follow
            # the second task. Its previous statistics must remain unchanged.
            teacher.locator("#teacher-task-picker").select_option(first_task_id)
            expect(teacher.locator("#current-task")).to_contain_text(title)
            expect(teacher.locator("#submitted")).to_have_text("3")
            expect(teacher.locator("#accepted")).to_have_text("0")
            expect(teacher.locator("#failed")).to_have_text("0")
            assert student_state(student)["task"]["id"] == next_task_id
            expect(student.locator("#task-title")).to_have_text(next_title)
            teacher.screenshot(path=str(evidence / "ux-first-task-history.png"), full_page=True)
            teacher.locator("#teacher-task-picker").select_option("")
            expect(teacher.locator("#current-task")).to_contain_text(next_title)
            expect(teacher.locator("#submitted")).to_have_text("0")
        last_title = next_title
    expect(teacher.locator("#notebook-overview")).to_contain_text(LECTURE.name)
    # Replacing the Notebook must work in-place, without publishing or altering the task.
    large = {"nbformat": 4, "nbformat_minor": 4, "metadata": {}, "cells": []}
    for i in range(135):
        source = "int main() { return 0; }\n"
        meta = {}
        if i in (0, 29, 58, 87, 116):
            source = "// @classlab exercise\n" + source
        if i == 8:
            source = "// @classlab answer\n" + source
        if i == 10:
            source = "// @classlab exercise: Malformed metadata\n" + source
            meta = {"classlab": {"testCases": [{"name": "missing fields"}]}}
        large["cells"].append({"cell_type": "code", "source": source, "metadata": meta,
                               "execution_count": None, "outputs": []})
    upload.set_input_files({"name": "large.ipynb", "mimeType": "application/json",
                            "buffer": json.dumps(large).encode()})
    expect(teacher.locator("#notebook-overview")).to_contain_text("Total cells: 135")
    expect(teacher.locator("#notebook-overview")).to_contain_text("Interactive exercises: 5")
    expect(teacher.locator("#notebook-overview")).to_contain_text("Needs review: 1")
    expect(teacher.locator("#notebook-list button")).to_have_count(5)
    expect(teacher.locator("#notebook-list button").first).to_contain_text("ClassLab Exercise · Cell 1")
    teacher.locator("#notebook-filter").select_option("all")
    for num in (9, 11):
        teacher.locator("#notebook-list button").filter(has_text=f"Cell {num} ·").click()
        expect(teacher.locator("#use-notebook-cell")).to_be_hidden()
        expect(teacher.locator("#toggle-prep-cell")).to_be_hidden()
    upload.set_input_files(ROOT / "examples/classlab-demo.ipynb")
    expect(teacher.locator("#notebook-overview")).to_contain_text("Interactive exercises: 0")
    expect(teacher.locator("#notebook-filter")).to_have_value("all")
    expect(teacher.locator("#notebook-list button")).to_have_count(3)
    expect(teacher.locator("#current-task")).to_contain_text(last_title)
    assert not errors, errors
    for student in students:
        student.close()
    teacher.close()
    print("Notebook classroom browser acceptance passed: direct import, 74/5 filter, safe replacement, private metadata, real submissions, ungraded submissions, analytics, and all five exercises published in sequence.")


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
