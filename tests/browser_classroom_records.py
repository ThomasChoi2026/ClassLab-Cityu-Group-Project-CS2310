"""Exercise archival navigation and room isolation against the normal server."""
import argparse

from playwright.sync_api import expect, sync_playwright


def check(browser, base):
    teacher = browser.new_page()
    other_teacher = browser.new_page()
    student = browser.new_page(viewport={"width": 390, "height": 844})
    errors = []
    for page in (teacher, other_teacher, student):
        page.on("pageerror", lambda error: errors.append(str(error)))

    def create(page, name):
        page.goto(base)
        page.locator("#create input").fill(name)
        page.locator("#create button").first.click()
        link = page.locator("#join-link")
        expect(link).not_to_have_value("")
        return link.input_value()

    def publish(page, title, code, tests=False):
        page.locator("[name=title]").fill(title)
        page.locator("[name=starterCode]").fill(code)
        if tests:
            page.locator("#teacher-optional-settings summary").click()
            page.locator("#add-case").click()
            page.locator("#case-editor-rows [data-field=name]").fill("Teacher only")
            page.locator("#case-editor-rows [data-field=visibility]").select_option("hidden")
            page.locator("#case-editor-rows [data-field=expectedOutput]").fill("PRIVATE_ANSWER")
        with page.expect_response(lambda response: response.url.endswith("/tasks") and
                                  response.request.method == "POST") as published:
            page.locator("#publish-task").click()
        assert published.value.status == 201, published.value.text()
        return published.value.json()["id"]

    def join(link):
        student.goto(link)
        student.locator("#join input").fill("Ada")
        student.locator("#join button").click()
        expect(student.locator("#student-name")).to_have_text("Ada")

    def credentials(link):
        room = link.rsplit("/", 1)[1]
        key = student.evaluate("room => localStorage.getItem('classlab.student.' + room)", room)
        return f"{base}/api/rooms/{room}", {"X-Student-Key": key}

    alpha = create(teacher, "Records Alpha")
    beta = create(other_teacher, "Records Beta")
    join(alpha)
    first = publish(teacher, "First lesson", "int main() { return 1; }", tests=True)
    editor = student.locator("#student-code")
    code = "int main() { return 10; }"
    expect(editor).to_have_value("int main() { return 1; }")
    editor.fill(code)
    student.locator("#submit-code").click()
    expect(teacher.locator("#attempts")).to_have_text("1")
    second = publish(teacher, "Second lesson", "int main() { return 2; }")
    expect(editor).to_have_value("int main() { return 2; }")

    teacher_picker = teacher.locator("#teacher-task-picker")
    student_picker = student.locator("#student-task-picker")
    teacher_picker.select_option(first)
    expect(teacher.locator("#current-task")).to_have_text("往期任务 · First lesson")
    expect(teacher.locator("#attempts")).to_have_text("1")
    expect(teacher.locator("#students").get_by_role("button", name="移出")).to_have_count(0)
    teacher.get_by_role("button", name="查看提交").click()
    expect(teacher.locator("#submission-dialog")).to_be_visible()
    expect(teacher.locator("#full-source")).to_contain_text(code)
    teacher.locator("#submission-dialog").get_by_role("button", name="关闭").click()

    student_picker.select_option(first)
    expect(student.locator("#task-title")).to_have_text("First lesson")
    expect(student.locator("#archive-notice")).to_be_visible()
    expect(editor).to_have_value(code)
    expect(editor).not_to_be_editable()
    expect(student.locator("#run-code")).to_be_disabled()
    expect(student.locator("#submit-code")).to_be_hidden()
    expect(student.locator("#history-list li")).to_have_count(1)
    alpha_api, alpha_key = credentials(alpha)
    archived = student.request.get(f"{alpha_api}/task?taskId={first}", headers=alpha_key)
    assert archived.ok
    assert "PRIVATE_ANSWER" not in archived.text() and "Teacher only" not in archived.text()
    assert student.request.get(f"{alpha_api}/progress?taskId={first}", headers=alpha_key).status == 403
    assert student.request.post(f"{alpha_api}/submissions", headers=alpha_key,
                                data={"taskId": first, "code": code}).status == 409
    assert student.request.post(f"{alpha_api}/run", headers=alpha_key,
                                data={"taskId": first, "code": code, "input": ""}).status == 409

    third = publish(teacher, "Third lesson", "int main() { return 3; }")
    expect(teacher.locator("#current-task")).to_have_text("当前任务 · Third lesson")
    expect(teacher.locator("#attempts")).to_have_text("0")
    expect(student_picker.locator("option").first).to_have_text("最新发布 · Third lesson")
    expect(student.locator("#task-title")).to_have_text("First lesson")
    student_picker.select_option(second)
    expect(editor).to_have_value("int main() { return 2; }")
    student_picker.select_option("")
    expect(editor).to_have_value("int main() { return 3; }")
    expect(editor).to_be_editable()
    expect(student.locator("#submit-code")).to_be_enabled()
    assert third != second
    teacher_picker.select_option(first)
    expect(teacher.locator("#current-task")).to_have_text("往期任务 · First lesson")
    teacher.locator("#toggle-classroom").click()
    expect(teacher.locator("#projection-task")).to_have_text("Third lesson")

    beta_task = publish(other_teacher, "Beta task", "int main() { return 4; }")
    join(beta)
    expect(editor).to_have_value("int main() { return 4; }")
    beta_api, beta_key = credentials(beta)
    assert student.request.get(f"{beta_api}/task?taskId={first}", headers=beta_key).status == 400
    assert student.request.get(f"{alpha_api}/task?taskId={beta_task}", headers=beta_key).status == 403
    student.locator("#student-classrooms summary").click()
    student.get_by_role("link", name="Records Alpha").click()
    expect(student.locator("#room-name")).to_have_text("Records Alpha")
    expect(editor).to_have_value("int main() { return 3; }")
    expect(student.locator("#join")).to_be_hidden()
    student.locator("#student-classrooms summary").click()
    student.get_by_role("link", name="Records Beta").click()
    expect(student.locator("#room-name")).to_have_text("Records Beta")
    expect(editor).to_have_value("int main() { return 4; }")
    assert not errors, errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--executable")
    args = parser.parse_args()
    with sync_playwright() as p:
        with p.chromium.launch(executable_path=args.executable) as browser:
            check(browser, args.url)
    print("Classroom records passed: three tasks, teacher details, read-only archives, private tests and two rooms.")
