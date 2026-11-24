"""Real Chromium plus real GCC, using the original marked Notebook source."""
import shutil
import sys
import tempfile
from pathlib import Path
from playwright.sync_api import expect, sync_playwright
from workflow import server
from interactive_scenarios import exercise_sources
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"judge"))
from trusted_native import NativeEvaluator, approved_sources, native_socket

def check(browser,base):
    starter,correct=exercise_sources()
    context=browser.new_context(viewport={"width":1050,"height":900})
    teacher=context.new_page()
    teacher.goto(base)
    teacher.locator("#create input").fill("Real GCC interactive")
    teacher.get_by_role("button",name="创建课堂",exact=True).click()
    expect(teacher.locator("#join-link")).not_to_have_value("")
    teacher.locator("#notebook-file").set_input_files(ROOT/"examples/CS2310_Score_Analysis.ipynb")
    teacher.locator("#notebook-list button").filter(has_text="Debug the accumulation loop").click()
    expect(teacher.locator("[name=starterCode]")).to_have_value(starter)
    teacher.locator("#publish-task").click()
    expect(teacher.locator("#publish-feedback")).to_contain_text("任务已发布")
    student=context.new_page()
    errors=[]
    student.on("pageerror",lambda e:errors.append(str(e)))
    student.goto(teacher.locator("#join-link").input_value())
    student.locator("#join input").fill("Ada")
    student.locator("#join button").click()
    editor=student.locator("#student-code")
    expect(editor).to_have_value(starter)
    run=student.locator("#run-code")
    send=student.locator("#send-stdin")
    field=student.locator("[name=runInput]")
    panel=student.locator("#run-result")
    expect(run).to_be_enabled()
    expect(field).to_be_hidden()
    run.click()
    expect(send).to_be_enabled(timeout=20000)
    expect(editor).to_have_attribute("readonly","")
    field.fill("5")
    send.click()
    expect(field).to_have_value("")
    student.wait_for_timeout(3200)
    expect(panel).to_contain_text("运行中")
    expect(send).to_be_enabled()
    field.fill("10 20");send.click();expect(field).to_have_value("")
    field.fill("30 40");send.click()
    expect(panel).to_contain_text("运行成功",timeout=12000)
    expect(panel.locator("pre")).to_have_text("100")
    expect(field).to_be_hidden()
    expect(run).to_be_enabled()
    editor.fill(correct)
    run.click()
    expect(send).to_be_enabled(timeout=20000)
    field.fill("5\n10 20 30 40 50")
    send.click()
    expect(panel.locator("pre")).to_have_text("150",timeout=12000)
    expect(panel).to_contain_text("运行成功")
    expect(teacher.locator("#attempts")).to_have_text("0")
    expect(run).to_be_enabled()
    run.click()
    expect(send).to_be_enabled(timeout=20000)
    student.locator("#stop-run").click()
    expect(panel).to_contain_text("已停止",timeout=10000)
    expect(run).to_be_enabled()
    editor.fill(correct+"\n// unapproved")
    run.click()
    expect(panel).to_contain_text("未经本地操作人员审查",timeout=10000)
    assert not errors,errors
    context.close()
    print("Real Chromium + GCC: original notebook, incremental input after 3.2s, 100/150, Stop, reviewed source gate.",flush=True)

if __name__=="__main__":
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp);sock=path/"judge.sock"
        evaluator=NativeEvaluator(shutil.which("g++"),approved_sources())
        with native_socket(sock,evaluator),server(path/"rooms.json",sock) as base,sync_playwright() as p:
            browser=p.chromium.launch()
            try:
                check(browser,base)
            finally:
                browser.close()
