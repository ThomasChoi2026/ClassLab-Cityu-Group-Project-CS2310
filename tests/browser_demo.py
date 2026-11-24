"""Optional smoke test against demo/run.py, using fresh headless Chromium contexts."""
import argparse
import csv
import re
from io import BytesIO, StringIO
from pathlib import Path
from urllib.parse import urlparse

import zxingcpp
from PIL import Image
from playwright.sync_api import expect, sync_playwright


def rehearse(browser, base, evidence_dir=None):
    if evidence_dir is not None:
        evidence_dir.mkdir(parents=True, exist_ok=True)
    teacher = browser.new_page()
    errors = []
    teacher.on("pageerror", lambda error: errors.append(str(error)))
    teacher.goto(base)
    expect(teacher.locator("#demo-banner")).to_be_visible()
    teacher.locator("#create input").fill("CS2310 rehearsal")
    teacher.get_by_role("button", name="Create classroom", exact=True).click()
    qr = teacher.locator("#show-qr")
    expect(qr).to_be_visible()
    image = Image.open(BytesIO(qr.screenshot()))
    decoded = zxingcpp.read_barcode(image)
    assert decoded and decoded.text == teacher.locator("#join-link").input_value()
    assert urlparse(decoded.text).netloc == urlparse(base).netloc

    teacher.locator("#compose-prep").click()
    expect(teacher.locator("#notebook-file")).to_be_visible()
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
    teacher.locator("#teacher-optional-settings").evaluate("(element) => element.open = true")
    # Legacy fixtures remain supported through the ordinary test editor.
    # The obsolete demo-only button is intentionally gone from the teacher UI.
    expect(teacher.locator("#demo-cases")).to_have_count(0)
    for name, stdin, output, visibility in [
        ("Positive", "2 3", "5", "public"), ("Zero", "0 0", "0", "public"),
        ("Mixed signs", "-4 9", "5", "hidden"),
    ]:
        teacher.locator("#add-case").click()
        row = teacher.locator("#case-editor-rows .case-row").last
        row.locator("[data-field=name]").fill(name)
        row.locator("[data-field=input]").fill(stdin)
        row.locator("[data-field=expectedOutput]").fill(output)
        row.locator("[data-field=visibility]").select_option(visibility)
    teacher.locator("#publish-task").click()
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
        expect(page.locator("#run-result")).to_contain_text("The current code will not run")
        page.locator("[name=runInput]").fill("2 3")
        page.locator("#run-code").click()
        expect(page.locator("#run-result")).to_contain_text("Prerecorded result")
        expect(page.locator("#run-result")).to_contain_text("5" if change else "-1")
        expect(page.locator("#stdin-panel")).to_be_hidden()
        page.context.grant_permissions(["clipboard-read", "clipboard-write"], origin=base)
        page.locator("#copy-run-result").click()
        expect(page.locator("#run-copy-feedback")).to_have_text("Run result copied.")
        copied = page.evaluate("navigator.clipboard.readText()")
        assert "DEMO REPLAY" in copied and "Prerecorded result" in copied
        assert "Standard output:" in copied
        assert ("5" in copied) if change else ("-1" in copied)
        page.evaluate("""() => Object.defineProperty(navigator, "clipboard", {
            configurable: true,
            value: { writeText: () => Promise.reject(new Error("clipboard blocked")) }
        })""")
        page.locator("#copy-run-result").click()
        expect(page.locator("#run-copy-fallback")).to_be_visible()
        expect(page.locator("#run-copy-feedback")).to_contain_text("Text selected")
        if evidence_dir is not None and index == 2:
            page.screenshot(path=str(evidence_dir / "student-run-replay.png"), full_page=True)
        code.press("Control+Enter")
        result = page.locator("#student-result")
        expect(result).to_contain_text("All tests passed" if change else "Wrong answer", timeout=15000)
        expect(result).to_contain_text("Prerecorded result. The current C++ code was neither compiled nor run.")
        assert "-4 9" not in result.inner_text()
        page.close()

    expect(teacher.locator("#submitted")).to_have_text("3", timeout=8000)
    expect(teacher.locator("#accepted")).to_have_text("2")
    expect(teacher.locator("#failed")).to_have_text("1")
    with teacher.expect_download() as csv_download:
        teacher.locator("#export-current-csv").click()
    csv_raw = Path(csv_download.value.path()).read_bytes()
    assert csv_raw.startswith(b"\xef\xbb\xbf")
    csv_rows = list(csv.DictReader(StringIO(csv_raw.decode("utf-8-sig"))))
    assert len(csv_rows) == 3
    assert {row["Mode"] for row in csv_rows} == {"Demo"}
    assert {row["Latest Submission Status"] for row in csv_rows} == {
        "All tests passed", "Tests not all passed (wrong answer)"
    }
    assert all("Student Session" not in key and "Code" not in key for key in csv_rows[0])
    if evidence_dir is not None:
        teacher.screenshot(path=str(evidence_dir / "teacher-dashboard.png"), full_page=True)
    patterns = teacher.locator("#edit-patterns")
    expect(patterns).to_contain_text("All tests passed 2 students")
    patterns.get_by_role("button").click()
    expect(teacher.locator("#diff-summary")).to_contain_text("Lines added: 1; lines removed: 1")
    expect(teacher.locator(".diff-del")).to_contain_text("a - b")
    expect(teacher.locator(".diff-add")).to_contain_text("a + b")
    if evidence_dir is not None:
        teacher.screenshot(path=str(evidence_dir / "teacher-common-edit.png"), full_page=True)
    assert not errors, errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--chromium", help="path to an installed Chromium-family browser")
    parser.add_argument("--evidence-dir", type=Path, help="save genuine browser screenshots")
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.chromium)
        try:
            rehearse(browser, args.url, args.evidence_dir)
            print("Browser demo passed: QR, Notebook, labeled Run-first fixture playback, three student submissions, teacher counts and diff.")
        finally:
            browser.close()
