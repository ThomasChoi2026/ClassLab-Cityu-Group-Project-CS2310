"""Optional browser check for editor actions, private history and the external handoff.

The external request is intercepted, so the browser sends no code to OPT CPP.
"""
import argparse
import json
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import expect, sync_playwright

EXTERNAL = "https://dive4dec.github.io/OPT_CPP/visualize.html"


def check(browser, base):
    context = browser.new_context(viewport={"width": 320, "height": 850}, accept_downloads=True)
    external = []
    def intercept(route):
        external.append(route.request.url)
        route.fulfill(content_type="text/html", body="<title>Handoff test</title>")

    context.route("https://dive4dec.github.io/**", intercept)
    teacher = context.new_page()
    teacher.goto(base)
    teacher.locator("#create input").fill("Browser test")
    teacher.locator("#create button:not([type])").click()
    join = teacher.locator("#join-link")
    expect(join).to_be_visible()
    teacher.locator("[name=title]").fill('A/B: "Test"')
    teacher.locator("[name=description]").fill("Synthetic exercise")
    starter = "int main() {}"
    teacher.locator("[name=starterCode]").fill(starter)
    teacher.locator("#publish-task").click()
    expect(teacher.locator("#publish-feedback")).to_contain_text("Task published")

    student = context.new_page()
    errors = []
    student.on("pageerror", lambda error: errors.append(str(error)))
    student.goto(join.input_value())
    student.locator("#join input").fill("Student A")
    student.locator("#join button").click()
    editor = student.locator("#student-code")
    expect(editor).to_have_value(starter)
    stdin = student.locator("[name=runInput]")
    expect(student.locator("#stdin-panel")).to_be_hidden()
    expect(stdin).to_be_hidden()
    expect(student.locator("#optcpp-options, #optcpp-input, #copy-opt-input")).to_have_count(0)
    expect(student.locator("#submit textarea")).to_have_count(2)  # editor and native Run-first stdin
    expect(student.locator("#run-code")).to_be_disabled()
    expect(student.locator(".editor-field #open-optcpp")).to_have_text("Send to OPT CPP")
    assert student.evaluate("document.documentElement.scrollWidth === innerWidth")
    assert student.evaluate("""() => {
        const row = document.querySelector(".editor-field .section-heading");
        return row.scrollWidth === row.clientWidth;
    }""")
    code = "// synthetic café & # + %\nint main() { return 0; }\n"
    samples = (
        code,
        "#include <iostream>\nint main() { int x; std::cin >> x; std::cout << x; }",
        "#include <iostream>\nint main() { int a, b; std::cin >> a; std::cin >> b; std::cout << a+b; }",
    )
    assert not external
    for sample in samples:
        editor.fill(sample)
        expect(stdin).to_be_hidden()
        # Baseline main's exact URL construction when its optional field is empty.
        # The new popup URL must be byte-identical, not merely use the same host.
        baseline = student.evaluate("""code => {
            const optionalInput = "";
            return "https://dive4dec.github.io/OPT_CPP/visualize.html#" + new URLSearchParams({
                code, curInstr: "0", mode: "display", py: "cpp",
                rawInputLstJSON: JSON.stringify(optionalInput === "" ? [] : [optionalInput])
            });
        }""", sample)
        with student.expect_popup() as opened:
            student.locator("#open-optcpp").click()
        popup = opened.value
        popup.wait_for_load_state("domcontentloaded")
        assert popup.url == baseline, (popup.url, baseline)
        state = parse_qs(urlsplit(popup.url).fragment)
        assert state["code"] == [sample]
        assert json.loads(state["rawInputLstJSON"][0]) == []
        assert state["mode"] == ["display"]
        assert popup.evaluate("window.opener === null")
        popup.close()
    editor.fill(code)

    with student.expect_download() as downloaded:
        student.locator("#download-code").click()
    download = downloaded.value
    assert download.suggested_filename.endswith(".cpp") and "/" not in download.suggested_filename
    assert download.path().read_bytes() == code.encode()
    editor.fill("// long " + "€" * 3000)
    student.locator("#open-optcpp").click()
    expect(student.locator("#optcpp-fallback")).to_be_visible()
    assert len(external) == len(samples)
    if browser.browser_type.name == "chromium":
        context.grant_permissions(["clipboard-read", "clipboard-write"], origin=base)
        student.locator("#copy-opt-code").click()
        expect(student.locator("#optcpp-status")).to_have_text("Current code copied.")
        assert student.evaluate("navigator.clipboard.readText()") == "// long " + "€" * 3000
    with student.expect_popup() as blank:
        student.get_by_role("link", name="Open blank OPT CPP").click()
    blank.value.wait_for_load_state("domcontentloaded")
    assert blank.value.url == EXTERNAL
    blank.value.close()
    expect(teacher.locator("#attempts")).to_have_text("0")

    student.once("dialog", lambda dialog: dialog.dismiss())
    student.locator("#reset-code").click()
    expect(editor).to_have_value("// long " + "€" * 3000)
    student.once("dialog", lambda dialog: dialog.accept())
    student.locator("#reset-code").click()
    expect(editor).to_have_value(starter)
    student.reload()
    expect(editor).to_have_value(starter)
    for attempt in (1, 2):
        student.get_by_role("button", name="Submit code").click()
        expect(student.locator("#history-list li")).to_have_count(attempt)
    student.locator("#submission-history summary").click()
    expect(student.locator("#history-list li").first).to_contain_text("Submitted")
    expect(teacher.locator("#attempts")).to_have_text("2")
    assert not errors, errors
    context.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--browser", choices=("chromium", "firefox", "webkit"), default="chromium")
    parser.add_argument("--executable")
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = getattr(playwright, args.browser).launch(executable_path=args.executable)
        try:
            check(browser, args.url)
            print("Student browser check passed: teammate OPT CPP one-click handoff, baseline-identical empty-input handoff, fallback, mobile layout, reset and history.")
        finally:
            browser.close()
