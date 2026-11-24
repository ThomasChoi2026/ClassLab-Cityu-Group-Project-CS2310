"""Browser acceptance for the teacher's two workspaces and Notebook cell browser.

Run against a normal or demo ClassLab HTTP server. Requires Python Playwright.
Does not enable or exercise arbitrary C++ execution.
"""
import argparse
import json
import re

from playwright.sync_api import expect, sync_playwright


def synthetic_notebook():
    cells = [
        {"cell_type": "markdown", "source": ["# Intro\n", "Example lesson text\n"]},
        {"cell_type": "code", "source": [
            "%%cpp\n", "#include <iostream>\n", "int main() { std::cout << 2; }\n"
        ]},
        {"cell_type": "code", "source": ["%%hermes\n", "int hermes_cell = 3;\n"]},
        {"cell_type": "code", "source": ["from __init__ import *\n"]},
    ]
    cells += [
        {"cell_type": "code", "source": ["%%cpp\n", f"int sample_{i} = {i};\n"]}
        for i in range(4, 125)
    ]
    return {"nbformat": 4, "nbformat_minor": 5, "metadata": {}, "cells": cells}


def check(browser, base):
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(base)

    # Preparation must work even before a classroom is created.
    page.locator("#open-preparation").click()
    expect(page.locator("#compose-prep")).to_have_attribute("aria-pressed", "true")
    expect(page.locator("#publish-task")).to_be_disabled()
    expect(page.locator("#notebook-file")).to_be_visible()
    expect(page.locator("#prep-library")).not_to_have_attribute("open", "")
    expect(page.locator("#teacher-optional-settings")).not_to_have_attribute("open", "")
    expect(page.locator("#demo-banner")).to_be_hidden()
    download = page.get_by_role("link", name="下载教学 Notebook 示例（74 Cells / 5 题）")
    expect(download).to_be_visible()
    expect(download).to_have_attribute("href", re.compile(r"/blob/main/examples/CS2310_Score_Analysis\.ipynb$"))
    assert page.locator("#notebook-import").evaluate("(el) => el.compareDocumentPosition(document.querySelector('[name=title]')) & Node.DOCUMENT_POSITION_FOLLOWING")

    notebook = synthetic_notebook()
    page.locator("#notebook-file").set_input_files({
        "name": "synthetic-classlab.ipynb",
        "mimeType": "application/x-ipynb+json",
        "buffer": json.dumps(notebook).encode("utf-8"),
    })
    expect(page.locator("#notebook-list button")).to_have_count(len(notebook["cells"]))
    expect(page.locator("#notebook-current-label")).to_contain_text("Cell 1")

    page.locator("#notebook-filter").select_option("cpp")
    expect(page.locator("#notebook-list button")).to_have_count(len(notebook["cells"]) - 3)
    page.locator("#notebook-search").fill("sample_124")
    expect(page.locator("#notebook-list button")).to_have_count(1)
    expect(page.locator("#notebook-list button")).to_contain_text("Cell 125")
    page.locator("#notebook-search").fill("")
    page.locator("#notebook-filter").select_option("all")

    page.get_by_role("button", name=re.compile(r"^Cell 2 ·")).click()
    page.locator("#use-notebook-cell").click()
    expect(page.locator("[name=starterCode]")).to_have_value(re.compile(r"#include <iostream>"))
    assert not page.locator("[name=starterCode]").input_value().startswith("%%cpp")
    expect(page.locator("#notebook-combination")).not_to_have_attribute("open", "")
    page.locator("#notebook-combination summary").click()
    page.locator("#toggle-prep-cell").click()
    page.get_by_role("button", name=re.compile(r"^Cell 125 ·")).click()
    page.locator("#toggle-prep-cell").click()
    page.locator("#assemble-notebook").click()
    combined = page.locator("[name=starterCode]").input_value()
    assert combined.index("int main()") < combined.index("sample_124"), combined
    assert "%%cpp" not in combined

    page.get_by_role("button", name=re.compile(r"^Cell 3 ·")).click()
    before = page.locator("[name=starterCode]").input_value()
    page.locator("#use-notebook-cell").click()
    expect(page.locator("#notebook-status")).to_contain_text("%%hermes")
    assert page.locator("[name=starterCode]").input_value() == before

    page.get_by_role("button", name=re.compile(r"^Cell 4 ·")).click()
    page.locator("#use-notebook-cell").click()
    expect(page.locator("#notebook-status")).to_contain_text("Python")
    assert page.locator("[name=starterCode]").input_value() == before

    page.locator("[name=title]").fill("Prepared lesson")
    page.locator("#prep-library summary").click()
    page.locator("#save-draft").click()
    expect(page.locator("#draft-library option")).to_have_count(2)
    page.locator("#compose-quick").click()
    expect(page.locator("#prep-library")).to_be_hidden()
    expect(page.locator("#notebook-import")).to_be_hidden()
    expect(page.locator("#teacher-optional-settings")).not_to_have_attribute("open", "")
    page.locator("[name=title]").fill("Temporary quick task")
    page.locator("[name=starterCode]").fill('int main() { return 0; }')
    page.locator("#compose-prep").click()
    expect(page.locator("[name=title]")).to_have_value("Prepared lesson")
    assert "sample_124" in page.locator("[name=starterCode]").input_value()
    page.locator("#compose-quick").click()
    expect(page.locator("[name=title]")).to_have_value("Temporary quick task")
    expect(page.locator("[name=starterCode]")).to_have_value('int main() { return 0; }')

    page.locator("#exit-preparation").click()
    page.locator("#create input").fill("Teacher UX smoke test")
    page.locator("#create button").first.click()
    page.locator("#publish-task").click()
    expect(page.locator("#publish-feedback")).to_contain_text("任务已发布")
    expect(page.locator("[name=title]")).to_have_value("")

    # Quick publishing must not destroy an in-progress prepared lesson.
    page.locator("#compose-prep").click()
    expect(page.locator("[name=title]")).to_have_value("Prepared lesson")
    assert "sample_124" in page.locator("[name=starterCode]").input_value()

    student = context.new_page()
    student.on("pageerror", lambda error: errors.append(str(error)))
    student.goto(page.locator("#join-link").input_value())
    student.locator("#join input").fill("Student UX")
    student.locator("#join button").click()
    expect(student.locator("#task-title")).to_have_text("Temporary quick task")
    expect(student.locator("#student-code")).to_have_value('int main() { return 0; }')
    assert not errors, errors
    context.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="ClassLab teacher page, e.g. http://127.0.0.1:8080")
    parser.add_argument("--browser", choices=("chromium", "firefox", "webkit"), default="chromium")
    parser.add_argument("--executable")
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = getattr(playwright, args.browser).launch(executable_path=args.executable)
        try:
            check(browser, args.url)
            print("Teacher UX test passed: notebook filtering, magics, draft separation and quick publishing")
        finally:
            browser.close()
