"""Browser E2E for native Judge Run-first UI using an explicit mock Unix Judge.

Only fixed strings reach the mock. This does not execute untrusted C++ or
claim to verify the real Docker/gVisor sandbox.
"""
import argparse
from pathlib import Path
import tempfile

from playwright.sync_api import expect, sync_playwright
from judge_protocol import mock
from workflow import server


def check(browser):
    with tempfile.TemporaryDirectory() as directory:
        location = Path(directory)
        socket = location / "judge.sock"
        with mock(socket), server(location / "rooms.json", socket) as base:
            context = browser.new_context(viewport={"width": 1024, "height": 850})
            teacher = context.new_page()
            teacher.goto(base)
            teacher.locator("#create input").fill("Run-first class")
            teacher.locator("#create button:not([type])").click()
            join = teacher.locator("#join-link").input_value()
            teacher.locator("[name=title]").fill("Native run")
            teacher.locator("[name=starterCode]").fill("NO_STDIN")
            teacher.locator("#publish-task").click()
            expect(teacher.locator("#publish-feedback")).to_contain_text("任务已发布")

            student = context.new_page()
            student.goto(join)
            student.locator("#join input").fill("Ada")
            student.locator("#join button").click()
            editor = student.locator("#student-code")
            field = student.locator("#stdin-panel")
            typed = student.locator("[name=runInput]")
            expect(field).to_be_hidden()
            expect(student.locator("#run-code")).to_be_enabled()
            editor.fill("NO_STDIN")
            student.locator("#run-code").click()
            expect(student.locator("#run-result")).to_contain_text("Hello")
            expect(field).to_be_hidden()

            editor.fill("READS_INPUT")
            expect(field).to_be_hidden()
            student.locator("#run-code").click()
            expect(field).to_be_visible()
            expect(student.locator("#run-result")).to_contain_text("Enter a value:")
            expect(student.locator("#run-code")).to_have_text("提供输入并重新运行")
            typed.fill("5 3")
            student.locator("#run-code").click()
            expect(student.locator("#run-result")).to_contain_text("8")
            expect(field).to_be_hidden()
            expect(student.locator("#run-code")).to_have_text("运行代码")
            expect(teacher.locator("#attempts")).to_have_text("0")
            context.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("server_binary")
    parser.add_argument("--browser", choices=("chromium", "firefox", "webkit"), default="chromium")
    args = parser.parse_args()
    # workflow.server expects the classlab binary from argv[1] at import time.
    with sync_playwright() as playwright:
        browser = getattr(playwright, args.browser).launch()
        try:
            check(browser)
            print("Run-first native Judge mock browser test passed.")
        finally:
            browser.close()
