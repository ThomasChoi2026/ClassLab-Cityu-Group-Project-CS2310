"""Browser acceptance for the teacher's current-task CSV export."""
import argparse
import csv
import json
from io import StringIO
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def read_download_csv(download):
    raw = Path(download.path()).read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "CSV must include a UTF-8 BOM for Excel."
    return list(csv.DictReader(StringIO(raw.decode("utf-8-sig"))))


def check(browser, base):
    context = browser.new_context(accept_downloads=True)
    teacher = context.new_page()
    teacher.goto(base)
    teacher.locator("#create input").fill('Class, "CSV"')
    teacher.get_by_role("button", name="创建课堂", exact=True).click()
    join_link = teacher.locator("#join-link")
    expect(join_link).not_to_have_value("")
    join_url = join_link.input_value()
    room_id = join_url.rstrip("/").split("/")[-1]

    # No task: give a clear message and do not create an empty file.
    teacher.locator("#export-current-csv").click()
    expect(teacher.locator("#export-feedback")).to_contain_text("请先发布任务")

    teacher.locator("[name=title]").fill('Task, "CSV"')
    teacher.locator("[name=starterCode]").fill("int main() { return 0; }")
    teacher.locator("#publish-task").click()
    expect(teacher.locator("#publish-feedback")).to_contain_text("任务已发布")

    # One student submits with no Judge configured, so no score must be invented.
    student = context.new_page()
    student.goto(join_url)
    student.locator("#join input").fill('=HYPERLINK("https://example.invalid")')
    student.locator("#join button").click()
    student.locator("#student-code").fill("int main() { return 0; }")
    student.locator("#submit-code").click()
    expect(student.locator("#submit-feedback")).to_contain_text("代码已提交")

    # Add students with CSV-special names through the regular public join endpoint.
    for name in ['张三, "第二位"', "多行\n学生"]:
        created = teacher.evaluate(
            """async ({roomId, name}) => {
                const response = await fetch(`/api/rooms/${roomId}/students`, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({name})
                });
                return {status: response.status, body: await response.json()};
            }""",
            {"roomId": room_id, "name": name},
        )
        assert created["status"] == 201, created

    expect(teacher.locator("#joined")).to_have_text("3", timeout=8000)
    with teacher.expect_download() as pending_download:
        teacher.locator("#export-current-csv").click()
    download = pending_download.value
    assert download.suggested_filename.endswith(".csv")
    rows = read_download_csv(download)
    assert len(rows) == 3, rows
    expected_headers = [
        "Classroom Name", "Task Title", "Student Number", "Student Name",
        "Submission Count", "Latest Submission Status", "Passed Test Cases",
        "Total Test Cases", "Mode", "Exported At (UTC)",
    ]
    assert list(rows[0]) == expected_headers
    formula_name = "'=HYPERLINK(\"https://example.invalid\")"
    by_name = {row["Student Name"]: row for row in rows}
    assert set(by_name) == {
        formula_name,
        '张三, "第二位"',
        "多行\n学生",
    }, by_name
    formula_row = by_name[formula_name]
    assert formula_row["Classroom Name"] == 'Class, "CSV"'
    assert formula_row["Task Title"] == 'Task, "CSV"'
    assert formula_row["Latest Submission Status"] == "Submitted (not evaluated)"
    assert formula_row["Passed Test Cases"] == "" and formula_row["Total Test Cases"] == ""
    assert formula_row["Submission Count"] == "1"
    assert formula_row["Mode"] == "Trusted Native"
    assert all(row["Latest Submission Status"] == "Not submitted" for name, row in by_name.items()
               if name != formula_name)
    assert all(row["Passed Test Cases"] == "" and row["Total Test Cases"] == "" for row in rows)
    assert all(row["Exported At (UTC)"].endswith("Z") for row in rows)
    expect(teacher.locator("#export-feedback")).to_contain_text("已导出 3 名学生")

    # After the next task is published, old submissions must not carry into its CSV.
    teacher.locator("[name=title]").fill("Second task")
    teacher.locator("[name=starterCode]").fill("int main() { return 1; }")
    teacher.locator("#publish-task").click()
    expect(teacher.locator("#current-task")).to_contain_text("Second task")
    with teacher.expect_download() as next_download:
        teacher.locator("#export-current-csv").click()
    next_rows = read_download_csv(next_download.value)
    assert all(row["Task Title"] == "Second task" for row in next_rows)
    assert all(row["Submission Count"] == "0" for row in next_rows)
    assert all(row["Latest Submission Status"] == "Not submitted" for row in next_rows)
    assert all(row["Passed Test Cases"] == "" and row["Total Test Cases"] == "" for row in next_rows)

    # Verify every distinct teacher-visible latest-state category without inventing score values.
    synthetic_states = [
        {"number": 1, "name": "Not submitted", "count": 0, "latestStatus": "not_submitted"},
        {"number": 2, "name": "Queued", "count": 1, "latestStatus": "queued"},
        {"number": 3, "name": "Pending", "count": 1, "latestStatus": "pending"},
        {"number": 4, "name": "Judge unavailable", "count": 1, "latestStatus": "judge_unavailable"},
        {"number": 5, "name": "Judge error", "count": 1, "latestStatus": "judge_error"},
        {"number": 6, "name": "Queue full", "count": 1, "latestStatus": "judge_queue_full"},
        {"number": 7, "name": "Accepted", "count": 1, "latestStatus": "accepted", "passed": 3, "total": 3},
        {"number": 8, "name": "Wrong answer", "count": 1, "latestStatus": "wrong_answer", "passed": 1, "total": 3},
        {"number": 9, "name": "Compile error", "count": 1, "latestStatus": "compilation_error"},
        {"number": 10, "name": "Runtime error", "count": 1, "latestStatus": "runtime_error"},
        {"number": 11, "name": "Timed out", "count": 1, "latestStatus": "time_limit"},
        {"number": 12, "name": "Resource limited", "count": 1, "latestStatus": "resource_limit"},
    ]
    def synthetic_progress(route):
        response = route.fetch()
        state = response.json()
        state["students"] = synthetic_states
        route.fulfill(response=response, json=state)
    teacher.route("**/api/rooms/*/progress*", synthetic_progress)
    with teacher.expect_download() as synthetic_download:
        teacher.locator("#export-current-csv").click()
    synthetic_rows = read_download_csv(synthetic_download.value)
    statuses = {row["Student Name"]: row["Latest Submission Status"] for row in synthetic_rows}
    assert statuses == {
        "Not submitted": "Not submitted",
        "Queued": "Waiting for evaluation",
        "Pending": "Evaluating",
        "Judge unavailable": "Not evaluated (Judge unavailable)",
        "Judge error": "Evaluation service error",
        "Queue full": "Not evaluated (evaluation queue full)",
        "Accepted": "All tests passed",
        "Wrong answer": "Tests not all passed (wrong answer)",
        "Compile error": "Compilation error",
        "Runtime error": "Runtime error",
        "Timed out": "Time limit exceeded",
        "Resource limited": "Resource limit exceeded",
    }, statuses
    synthetic_by_name = {row["Student Name"]: row for row in synthetic_rows}
    assert synthetic_by_name["Accepted"]["Passed Test Cases"] == "3"
    assert synthetic_by_name["Accepted"]["Total Test Cases"] == "3"
    assert synthetic_by_name["Wrong answer"]["Passed Test Cases"] == "1"
    assert synthetic_by_name["Wrong answer"]["Total Test Cases"] == "3"
    for name in ["Not submitted", "Queued", "Pending", "Judge unavailable", "Judge error", "Queue full"]:
        assert synthetic_by_name[name]["Passed Test Cases"] == ""
        assert synthetic_by_name[name]["Total Test Cases"] == ""

    # An empty classroom must not create a misleading empty CSV.
    # Use a separate browser context so the previously created classroom's localStorage
    # cannot redirect this page straight to the dashboard. This scenario must start
    # from a genuinely empty teacher session.
    empty_context = browser.new_context(accept_downloads=True)
    empty_teacher = empty_context.new_page()
    empty_teacher.goto(base)
    empty_teacher.locator("#create input").fill("Empty classroom")
    empty_teacher.get_by_role("button", name="创建课堂", exact=True).click()
    empty_teacher.locator("[name=title]").fill("No students yet")
    empty_teacher.locator("[name=starterCode]").fill("int main() {}")
    empty_teacher.locator("#publish-task").click()
    expect(empty_teacher.locator("#publish-feedback")).to_contain_text("任务已发布")
    empty_teacher.locator("#export-current-csv").click()
    expect(empty_teacher.locator("#export-feedback")).to_contain_text("还没有学生")
    empty_context.close()

    # Network/API failures should be reported and the button should recover.
    teacher.route("**/api/rooms/*/progress*", lambda route: route.abort())
    teacher.locator("#export-current-csv").click()
    expect(teacher.locator("#export-feedback")).to_contain_text("导出失败", timeout=5000)
    expect(teacher.locator("#export-current-csv")).to_be_enabled()
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
            print("Classroom CSV browser check passed: current-task-only data, unsubmitted students, status mapping, UTF-8 BOM, CSV quoting, formula protection, score blanks, Trusted Native mode, empty states and request failures.")
        finally:
            browser.close()
