"""Optional smoke test against demo/run.py, using fresh headless Chromium contexts."""
import argparse
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import zxingcpp
from PIL import Image
from playwright.sync_api import expect, sync_playwright


def rehearse(browser, base):
    teacher = browser.new_page()
    errors = []
    teacher.on("pageerror", lambda error: errors.append(str(error)))
    teacher.goto(base)
    expect(teacher.locator("#demo-banner")).to_be_visible()
    teacher.locator("#create input").fill("CS2310 rehearsal")
    teacher.get_by_role("button", name="创建课堂", exact=True).click()
    qr = teacher.locator("#show-qr")
    expect(qr).to_be_visible()
    image = Image.open(BytesIO(qr.screenshot()))
    decoded = zxingcpp.read_barcode(image)
    assert decoded and decoded.text == teacher.locator("#join-link").input_value()
    assert urlparse(decoded.text).netloc == urlparse(base).netloc

    teacher.locator("#compose-prep").click()
    teacher.locator(".notebook-import summary").click()
    notebook = Path(__file__).resolve().parents[1] / "examples/classlab-demo.ipynb"
    teacher.locator("#notebook-file").set_input_files(notebook)
    teacher.get_by_role("button", name=re.compile(r"^Cell 2 ·")).click()
    teacher.locator("#use-notebook-cell").click()
    starter = teacher.locator("[name=starterCode]")
    original = starter.input_value()
    assert "a - b" in original
    teacher.get_by_role("button", name=re.compile(r"^Cell 3 ·")).click()
    expect(starter).to_have_value(original)
    teacher.locator("[name=title]").fill("Fix addition")
    teacher.locator("[name=description]").fill("Return the sum.")
    teacher.locator("#demo-cases").click()
    teacher.locator("#publish button:not([type])").click()
    expect(teacher.locator("#current-task")).to_contain_text("Fix addition")

    for index, change in enumerate((False, True, True), 1):
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(decoded.text)
        page.locator("#join input").fill(f"Student {index}")
        page.locator("#join button").click()
        code = page.locator("#student-code")
        expect(code).to_have_value(original)
        if change:
            revised = original.replace("a - b", "a + b")
            code.fill(revised)
            page.reload()
            expect(code).to_have_value(revised)
        # Demonstrate the Run-first UI without executing arbitrary student C++.
        expect(page.locator("#run-code")).to_be_enabled()
        expect(page.locator("#stdin-panel")).to_be_hidden()
        page.locator("#run-code").click()
        expect(page.locator("#stdin-panel")).to_be_visible()
        expect(page.locator("#run-result")).to_contain_text("不会执行当前代码")
        page.locator("[name=runInput]").fill("2 3")
        page.locator("#run-code").click()
        expect(page.locator("#run-result")).to_contain_text("预置演示回放")
        expect(page.locator("#run-result")).to_contain_text("5" if change else "-1")
        expect(page.locator("#stdin-panel")).to_be_hidden()
        code.press("Control+Enter")
        result = page.locator("#student-result")
        expect(result).to_contain_text("全部通过" if change else "输出不符", timeout=15000)
        expect(result).to_contain_text("预置演示结果")
        assert "-4 9" not in result.inner_text()
        page.close()

    expect(teacher.locator("#submitted")).to_have_text("3", timeout=8000)
    expect(teacher.locator("#accepted")).to_have_text("2")
    expect(teacher.locator("#failed")).to_have_text("1")
    patterns = teacher.locator("#edit-patterns")
    expect(patterns).to_contain_text("全部通过 2 人")
    patterns.get_by_role("button").click()
    expect(teacher.locator("#diff-summary")).to_contain_text("新增 1 行，删除 1 行")
    expect(teacher.locator(".diff-del")).to_contain_text("a - b")
    expect(teacher.locator(".diff-add")).to_contain_text("a + b")
    assert not errors, errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--chromium", help="path to an installed Chromium-family browser")
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.chromium)
        try:
            rehearse(browser, args.url)
            print("Browser demo passed: QR, Notebook, labeled Run-first fixture playback, three student submissions, teacher counts and diff.")
        finally:
            browser.close()
