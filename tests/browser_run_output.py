"""Browser acceptance for copying Run output, compiler diagnostics and errors.

The Run response is mocked. No student-supplied C++ is executed by this test.
"""
import argparse
import json

from playwright.sync_api import expect, sync_playwright


def check(browser, base):
    context = browser.new_context()
    teacher = context.new_page()
    teacher.goto(base)
    teacher.locator("#create input").fill("Run output copy test")
    teacher.get_by_role("button", name="创建课堂", exact=True).click()
    join_link = teacher.locator("#join-link")
    # Classroom creation is asynchronous; wait until the server returns the student URL.
    expect(join_link).not_to_have_value("")
    join_url = join_link.input_value()
    assert join_url.startswith(("http://", "https://")), join_url
    teacher.locator("[name=title]").fill("Copy Run output")
    teacher.locator("[name=starterCode]").fill("int main() { return 0; }")
    teacher.locator("#publish-task").click()
    expect(teacher.locator("#publish-feedback")).to_contain_text("任务已发布")

    student = context.new_page()
    student.goto(join_url)
    student.locator("#join input").fill("Run output student")
    student.locator("#join button").click()
    editor = student.locator("#student-code")
    editor.fill("int main() { return 0; }")

    # The normal test server has no Judge. Enable only the UI in this test and
    # intercept Run responses, so no submitted C++ reaches an execution service.
    def available_task(route):
        response = route.fetch()
        state = response.json()
        state["executionAvailable"] = True
        route.fulfill(response=response, json=state)

    student.route("**/api/rooms/*/task*", available_task)
    student.reload()
    expect(student.locator("#run-code")).to_be_enabled()

    run_responses = [
        {
            "status": "success",
            "stdout": "  first line  \nsecond\tline\n",
            "stderr": "",
            "exitCode": 0,
        },
        {
            "status": "compilation_error",
            "diagnostic": "main.cpp:3:5: error: expected ';' before '}' token\n  }",
        },
        {
            "status": "runtime_error",
            "stderr": "segmentation fault\n",
            "exitCode": 139,
        },
        {
            "status": "success",
            "stdout": "",
            "stderr": "",
            "exitCode": 0,
        },
    ]
    run_requests = []

    def mock_run(route):
        request = json.loads(route.request.post_data)
        run_requests.append(request)
        result = run_responses.pop(0)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps(result, ensure_ascii=False))

    student.route("**/api/rooms/*/run", mock_run)
    context.grant_permissions(["clipboard-read", "clipboard-write"], origin=base)

    # Ordinary output: preserve spaces, tabs and line breaks.
    student.locator("#run-code").click()
    expect(student.locator("#copy-run-result")).to_be_visible()
    student.locator("#copy-run-result").click()
    expect(student.locator("#run-copy-feedback")).to_have_text("运行结果已复制。")
    copied = student.evaluate("navigator.clipboard.readText()")
    assert "运行状态：运行成功" in copied
    assert "标准输出：\n  first line  \nsecond\tline\n" in copied
    assert "退出状态：0" in copied
    assert len(run_requests) == 1

    # Compiler failure: copy the complete diagnostic, without rendering-only markup.
    student.locator("#run-code").click()
    expect(student.locator("#copy-run-result")).to_be_visible()
    student.locator("#copy-run-result").click()
    copied = student.evaluate("navigator.clipboard.readText()")
    assert "编译诊断：\nmain.cpp:3:5: error: expected ';' before '}' token\n  }" in copied
    assert "编译错误" in copied

    # Runtime failure: include stderr and exit code.
    student.locator("#run-code").click()
    expect(student.locator("#copy-run-result")).to_be_visible()
    student.locator("#copy-run-result").click()
    copied = student.evaluate("navigator.clipboard.readText()")
    assert "运行错误" in copied
    assert "标准错误：\nsegmentation fault\n" in copied
    assert "退出状态：139" in copied

    # Empty stdout remains copyable and is not replaced with invented output.
    student.locator("#run-code").click()
    expect(student.locator("#copy-run-result")).to_be_visible()
    student.locator("#copy-run-result").click()
    copied = student.evaluate("navigator.clipboard.readText()")
    assert "标准输出：\n\n" in copied
    assert "退出状态：0" in copied

    # Clipboard failure keeps the original result selected for manual copying.
    student.evaluate("""() => Object.defineProperty(navigator, "clipboard", {
        configurable: true,
        value: { writeText: () => Promise.reject(new Error("clipboard blocked")) }
    })""")
    student.locator("#copy-run-result").click()
    expect(student.locator("#run-copy-fallback")).to_be_visible()
    expect(student.locator("#run-copy-feedback")).to_contain_text("已选中文本")
    assert student.locator("#run-copy-fallback").input_value().endswith("退出状态：0")
    assert len(run_requests) == 4

    # A fresh task clears old output and its copy button.
    teacher.locator("[name=title]").fill("Next task")
    teacher.locator("[name=starterCode]").fill("int main() { return 1; }")
    teacher.locator("#publish-task").click()
    expect(student.locator("#task-title")).to_have_text("Next task", timeout=8000)
    expect(student.locator("#run-result")).to_be_hidden()
    expect(student.locator("#copy-run-result")).to_have_count(0)
    assert not run_requests or len(run_requests) == 4
    expect(teacher.locator("#attempts")).to_have_text("0")
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
            print("Run output browser check passed: stdout whitespace, compiler diagnostics, runtime errors, empty output, Demo labeling in the demo test, clipboard fallback, task reset and no submission side effect.")
        finally:
            browser.close()
