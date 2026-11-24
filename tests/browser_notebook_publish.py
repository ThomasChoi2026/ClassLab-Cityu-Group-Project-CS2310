"""Verify consecutive Notebook publication in Chromium with a synthetic lecture."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def check(browser, base, evidence):
    teacher = browser.new_page(viewport={"width": 1280, "height": 1050})
    student = browser.new_page()
    errors = []
    for page in (teacher, student):
        page.on("pageerror", lambda error: errors.append(str(error)))
    teacher.goto(base)
    teacher.locator("#create input").fill("Notebook workflow")
    teacher.locator("#create button").first.click()
    teacher.locator("#compose-prep").click()
    student.goto(teacher.locator("#join-link").input_value())
    student.locator("#join input").fill("Student")
    student.locator("#join button").click()
    expect(student.locator("#waiting")).to_be_visible()

    single = "int main() { return 0; }\n"
    dependency = "#include <iostream>\nint answer() { return 42; }\n"
    entry = "int main() { std::cout << answer(); }\n"
    markdown = "# 課堂練習\n先閱讀以下程式。"
    third = "int main() { return 3; }"
    cells = [
        {"cell_type": "code", "source": ["%%cpp\n", single]},
        {"cell_type": "markdown", "source": markdown},
        {"cell_type": "code", "source": dependency},
        {"cell_type": "code", "source": entry},
        {"cell_type": "code", "source": "%%hermes\nint answer = 42;"},
        {"cell_type": "code", "source": "%%cpp --flags\nint answer = 42;"},
        {"cell_type": "code", "source": "import sys\n"},
        {"cell_type": "code", "source": third},
    ]
    file = teacher.locator("#notebook-file")
    file.set_input_files({
        "name": "lesson.ipynb", "mimeType": "application/x-ipynb+json",
        "buffer": json.dumps({"nbformat": 4, "nbformat_minor": 5, "cells": cells}).encode(),
    })
    overview = teacher.locator("#notebook-overview")
    buttons = teacher.locator("#notebook-list button")
    expect(buttons).to_have_count(len(cells))
    title = teacher.locator("[name=title]")
    description = teacher.locator("[name=description]")
    starter = teacher.locator("[name=starterCode]")
    selection = teacher.locator("#selected-prep-cells")
    notice = teacher.locator("#publish-feedback")
    publish = teacher.locator("#publish-task")
    use = teacher.locator("#use-notebook-cell")
    toggle = teacher.locator("#toggle-prep-cell")
    search = teacher.locator("#notebook-search")

    def select(number):
        teacher.get_by_role("button", name=f"Cell {number} ·", exact=False).click()

    def expect_student(name, code):
        expect(student.locator("#task-title")).to_have_text(name)
        expect(student.locator("#student-code")).to_have_value(code)

    count = []
    teacher.on("request", lambda req: count.append(req.url) if req.method == "POST" and req.url.endswith("/tasks") else None)
    title.fill("First exercise")
    select(1)
    expect(teacher.locator("#notebook-status")).to_contain_text("这里只是预览")
    expect(starter).to_have_value("")
    publish.click()
    expect(notice).to_contain_text("让学生从空白开始")
    expect(student.locator("#waiting")).to_be_visible()
    assert count == []

    toggle.click()
    expect(selection).to_contain_text("尚未填入")
    publish.click()
    expect(notice).to_contain_text("所选组合尚未填入")
    assert count == []
    use.click()
    expect(teacher.locator("#notebook-status")).to_contain_text("已移除 %%cpp")
    expect(starter).to_have_value(single)
    select(2)
    teacher.locator("#append-notebook-text").click()
    expect(description).to_have_value(markdown)
    expect(starter).to_have_value(single)
    teacher.locator("#add-case").click()
    teacher.locator("#case-editor-rows [data-field=name]").fill("First case only")
    teacher.locator("#case-editor-rows [data-field=input]").fill("first")
    teacher.locator("#case-editor-rows [data-field=expectedOutput]").fill("0")
    if evidence:
        teacher.locator("#teacher-composer").screenshot(path=evidence / "after-teacher.png")
    publish.click()
    expect_student("First exercise", single)
    expect(student.locator("#task-description")).to_contain_text("先閱讀以下程式。")
    expect(student.locator("#student-public-tests")).to_contain_text("First case only")
    if evidence:
        student.screenshot(path=evidence / "after-student.png", full_page=True)
    student.locator("#student-code").fill("// student draft must not leak")
    expect(overview).to_contain_text("lesson.ipynb")
    expect(buttons).to_have_count(len(cells))
    expect(description).to_have_value("")
    expect(starter).to_have_value("")
    expect(teacher.locator("#case-editor-rows > *")).to_have_count(0)

    # Instructor selects in reverse order; assembly follows Notebook order.
    select(4)
    toggle.click()
    select(3)
    toggle.click()
    expect(selection).to_have_text("组合 Cell 3 → 4 尚未填入起始代码。")
    teacher.locator("#assemble-notebook").click()
    expect(selection).to_contain_text("已填入起始代码")
    combined = dependency.rstrip() + "\n\n" + entry.rstrip()
    expect(starter).to_have_value(combined)
    edited = combined.replace("return 42", "return 7")
    starter.fill(edited)
    title.fill("Second exercise")
    search.fill("answer")
    expect(teacher.locator("#notebook-current-label")).to_contain_text("Cell 3")
    teacher.route("**/api/rooms/*/tasks", lambda route: route.fulfill(
        status=503, json={"error": "测试用发布失败"}), times=1)
    publish.click()
    expect(notice).to_contain_text("测试用发布失败")
    expect(title).to_have_value("Second exercise")
    expect(starter).to_have_value(edited)
    expect(selection).to_contain_text("已填入起始代码")
    expect(overview).to_contain_text("lesson.ipynb")
    expect(student.locator("#task-title")).to_have_text("First exercise")
    publish.click()
    expect_student("Second exercise", edited)
    expect(student.locator("#task-description")).to_be_hidden()
    expect(student.locator("#public-tests")).to_be_hidden()
    expect(search).to_have_value("answer")
    expect(teacher.locator("#notebook-current-label")).to_contain_text("Cell 3")
    expect(selection).to_contain_text("尚未选择组合单元")
    expect(overview).to_contain_text("lesson.ipynb")
    assert "lesson.ipynb" in file.input_value()

    search.fill("")
    for number, reason in ((5, "%%hermes"), (6, "无参数的 %%cpp"), (7, "Python")):
        select(number)
        expect(teacher.locator("#notebook-status")).to_contain_text(reason)
        use.click()
        expect(starter).to_have_value("")
    select(8)
    use.click()
    expect(starter).to_have_value(third)
    title.fill("Third exercise")
    publish.click()
    expect_student("Third exercise", third)
    expect(overview).to_contain_text("lesson.ipynb")
    assert "lesson.ipynb" in file.input_value()

    title.fill("Open exercise")
    description.fill("Write your own program.")
    publish.click()
    expect(notice).to_contain_text("让学生从空白开始")
    teacher.locator("#allow-empty-starter").check()
    publish.click()
    expect_student("Open exercise", "")
    expect(student.locator("#task-description")).to_have_text("Write your own program.")
    expect(teacher.locator("#allow-empty-starter")).not_to_be_checked()
    expect(overview).to_contain_text("lesson.ipynb")

    student.locator("#student-code").fill(single)
    student.locator('#submit button[type=submit]').click()
    expect(teacher.locator("#submitted")).to_have_text("1")
    expect(teacher.locator("#attempts")).to_have_text("1")
    teacher.locator("#toggle-classroom").click()
    expect(teacher.locator("#classroom-view")).to_be_visible()
    expect(teacher.locator("#classroom-view")).to_contain_text("Open exercise")
    assert not errors, errors
    student.close()
    teacher.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--executable")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    if args.evidence:
        args.evidence.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        with playwright.chromium.launch(executable_path=args.executable) as browser:
            check(browser, args.url, args.evidence)
    print("Notebook publication passed: one import, three code tasks, explicit blank task, retry and classroom feedback.")
