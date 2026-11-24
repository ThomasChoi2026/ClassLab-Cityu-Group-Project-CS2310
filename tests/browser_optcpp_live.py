"""Real external execution acceptance, using synthetic source only.
Unlike browser_student.py, this test does NOT intercept the external website.
A network, compilation, prompt or output failure fails this job explicitly.
"""
import argparse
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

PREFIX = "#include <iostream>\nint main() {\n"
CASES = (
    ("no-input", PREFIX + 'std::cout << "CLASSLAB_NO_INPUT_17";\n}\n',
     (), "CLASSLAB_NO_INPUT_17"),
    ("one-input", PREFIX + 'int x;\nstd::cin >> x;\nstd::cout << "CLASSLAB_ONE_" << x*2;\n}\n',
     ("21",), "CLASSLAB_ONE_42"),
    ("multiple-inputs", PREFIX + 'int a, b;\nstd::cin >> a;\nstd::cin >> b;\nstd::cout << "CLASSLAB_MULTI_" << a+b;\n}\n',
     ("7", "13"), "CLASSLAB_MULTI_20"),
)


def last_step(page):
    last = page.locator("#jmpLastInstr")
    expect(last).to_be_visible(timeout=90000)
    if last.is_enabled():
        last.click()


def check(browser, base, evidence):
    evidence.mkdir(parents=True, exist_ok=True)
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    teacher = context.new_page()
    teacher.goto(base)
    teacher.locator("#create input").fill("OPT CPP synthetic acceptance")
    teacher.locator("#create button:not([type])").click()
    expect(teacher.locator("#join-link")).to_be_visible()
    teacher.locator("[name=title]").fill("Synthetic external test")
    teacher.locator("[name=starterCode]").fill("int main() {}")
    teacher.locator("#publish-task").click()
    expect(teacher.locator("#publish-feedback")).to_contain_text("任务已发布")
    student = context.new_page()
    student.goto(teacher.locator("#join-link").input_value())
    student.locator("#join input").fill("Synthetic student")
    student.locator("#join button").click()
    expect(student.locator("#student-code")).to_be_visible()
    for name, source, inputs, output in CASES:
        student.locator("#student-code").fill(source)
        expect(student.locator("#stdin-panel")).to_be_hidden()
        with student.expect_popup(timeout=30000) as opened:
            student.locator("#open-optcpp").click()
        popup = opened.value
        popup.set_default_timeout(90000)
        try:
            popup.wait_for_load_state("domcontentloaded", timeout=90000)
            assert popup.url.startswith("https://dive4dec.github.io/OPT_CPP/visualize.html"), popup.url
            expect(popup.locator("#executeBtn")).to_be_visible(timeout=90000)
            expect(popup.locator("#pyStdout")).to_be_hidden()
            popup.locator("#executeBtn").click()
            last_step(popup)
            for index, value in enumerate(inputs):
                field = popup.locator("#raw_input_textbox")
                expect(field).to_be_visible(timeout=90000)
                field.fill(value)
                popup.screenshot(path=str(evidence / f"{name}-prompt-{index+1}.png"))
                old = field.element_handle()
                popup.locator("#raw_input_submit_btn").click()
                # A fresh trace rebuilds the visualizer after each supplied input.
                popup.wait_for_function("(old) => !old.isConnected", arg=old, timeout=90000)
                last_step(popup)
            expect(popup.locator("#pyStdout")).to_have_value(output, timeout=90000)
            popup.screenshot(path=str(evidence / f"{name}-output.png"))
            print(f"Real external execution verified: {name} -> {output}", flush=True)
        except Exception:
            popup.screenshot(path=str(evidence / f"{name}-failure.png"))
            raise
        finally:
            popup.close()
    context.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            check(browser, args.url, args.evidence)
        finally:
            browser.close()
