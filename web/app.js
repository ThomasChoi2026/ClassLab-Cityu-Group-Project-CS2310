"use strict";

const byId = (id) => document.getElementById(id);
const interval = 2000;

class RequestError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function api(path, { data, headers = {}, timeoutMs = 8000 } = {}) {
  let response;
  let result;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const { signal } = controller;
  try {
    response = await fetch("/api" + path, data === undefined ? { headers, signal } : {
      signal,
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    result = await response.json().catch(() => null);
  } catch {
    throw new RequestError("连接中断，请稍后重试。", 0);
  } finally {
    clearTimeout(timeout);
  }
  if (!result) throw new RequestError("无法读取服务器响应，请检查预览连接。", 0);
  if (!response.ok) throw new RequestError(result.error || "请求失败。", response.status);
  return result;
}

function feedback(message, error = false, target = "feedback") {
  const node = byId(target);
  node.textContent = message;
  node.classList.toggle("error", error);
}

function onSubmit(id, action, target = "feedback") {
  byId(id).addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = event.submitter || form.querySelector("button:not([type=button])");
    if (button.disabled) return;
    button.disabled = true;
    feedback("", false, target);
    try {
      await action(Object.fromEntries(new FormData(form)));
    } catch (error) {
      feedback(error.message, true, target);
    } finally {
      button.disabled = false;
    }
  });
}

function poll(refresh, onError) {
  let running = false;
  const tick = async () => {
    if (running) return;
    running = true;
    try {
      await refresh();
    } catch (error) {
      onError(error);
    } finally {
      running = false;
    }
  };
  setInterval(tick, interval);
  return tick;
}

async function copyText(field, status, success) {
  try {
    await navigator.clipboard.writeText(field.value);
    byId(status).textContent = success;
  } catch {
    field.focus();
    field.select();
    byId(status).textContent = "已选中文本，请使用浏览器的复制操作。";
  }
}

function joinQr(link) {
  const code = qrcode(0, "M");
  code.addData(link, "Byte");
  code.make();

  const size = code.getModuleCount();
  const margin = 4;
  const canvasSize = size + 2 * margin;
  const namespace = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(namespace, "svg");
  svg.setAttribute("viewBox", "0 0 " + canvasSize + " " + canvasSize);
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("shape-rendering", "crispEdges");

  const background = document.createElementNS(namespace, "rect");
  background.setAttribute("width", canvasSize);
  background.setAttribute("height", canvasSize);
  background.setAttribute("fill", "#fff");

  const modules = document.createElementNS(namespace, "path");
  const squares = [];
  for (let row = 0; row < size; ++row) {
    for (let col = 0; col < size; ++col) {
      if (code.isDark(row, col)) squares.push("M" + (col + margin) + " " + (row + margin) + "h1v1h-1z");
    }
  }
  modules.setAttribute("d", squares.join(""));
  modules.setAttribute("fill", "#000");
  svg.append(background, modules);
  return svg;
}

const statusText = {
  received: "已提交",
  success: "运行成功",
  judge_unavailable: "未评测 · 执行器不可用",
  judge_error: "评测服务错误",
  pending: "评测中",
  queued: "等待评测",
  judge_queue_full: "未评测 · 队列已满",
  accepted: "全部通过",
  passed: "通过",
  wrong_answer: "输出不符",
  compilation_error: "编译错误",
  runtime_error: "运行错误",
  time_limit: "运行超时",
  resource_limit: "资源超限",
};

const categoryText = {
  missing_semicolon: "可能缺少分号",
  syntax: "语法诊断",
  undeclared_identifier: "未声明的标识符",
  type_mismatch: "类型不匹配",
  header_or_namespace: "头文件或命名空间诊断",
  other: "其他编译诊断",
};

function element(tag, text) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  return node;
}

function sampleBlock(test) {
  const block = element("div");
  const summary = test.status ? test.name + " · " + statusText[test.status] : test.name;
  block.append(element("strong", summary));
  for (const [field, label] of [["input", "标准输入"], ["expectedOutput", "预期输出"], ["actualOutput", "实际输出"]]) {
    if (Object.hasOwn(test, field)) {
      block.append(element("p", label), element("pre", test[field] || "（空）"));
    }
  }
  return block;
}

function displayResult(container, result, teacher = false) {
  container.replaceChildren();
  if (!result) return;
  const score = result.total === undefined ? "" : " · " + result.passed + "/" + result.total + " 通过";
  container.append(element("p", (statusText[result.status] || "结果未知") + score));
  if (result.diagnostic) container.append(element("pre", result.diagnostic));
  if (teacher) {
    for (const test of result.cases || []) {
      container.append(element("p", "用例 " + test.testId + " · " + (statusText[test.status] || "结果未知")));
    }
  } else {
    for (const test of result.cases || []) container.append(sampleBlock(test));
  }
}

function initializeTeacher() {
  const storageKey = "classlab.teacher";
  let credentials = JSON.parse(localStorage.getItem(storageKey) || "null");
  const headers = () => ({ "X-Teacher-Key": credentials.teacherKey });
  const endpoint = (suffix) => "/rooms/" + credentials.id + suffix;
  const link = byId("join-link");
  const qrButton = byId("show-qr");
  const qrDialog = byId("qr-dialog");
  const caseRows = byId("case-editor-rows");
  const addCase = byId("add-case");
  const submissionDialog = byId("submission-dialog");
  let analysisSignature;
  let configurationTask;

  addCase.addEventListener("click", () => {
    if (caseRows.childElementCount >= 12) return;
    const row = byId("case-template").content.firstElementChild.cloneNode(true);
    row.querySelector(".remove-case").addEventListener("click", () => {
      row.remove();
      addCase.disabled = false;
      addCase.focus();
    });
    caseRows.append(row);
    addCase.disabled = caseRows.childElementCount >= 12;
    row.querySelector("input").focus();
  });

  function detailButton(number, taskId) {
    const button = element("button", "查看提交");
    button.type = "button";
    button.className = "secondary";
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        const latest = await api(endpoint("/latest/" + number + "?taskId=" + encodeURIComponent(taskId)),
          { headers: headers() });
        byId("submission-title").textContent = latest.name + "的最新提交";
        byId("submission-code").textContent = latest.code;
        displayResult(byId("teacher-result"), latest.result, true);
        if (!submissionDialog.open) submissionDialog.showModal();
      } catch (error) {
        feedback(error.message, true);
      } finally {
        button.disabled = false;
      }
    });
    return button;
  }

  function renderAnalysis(state) {
    byId("case-analysis").hidden = !state.caseStats.length;
    if (configurationTask !== state.task?.id) {
      configurationTask = state.task?.id;
      const tests = state.task?.testCases || [];
      byId("teacher-case-config").replaceChildren(...tests.map((test) => sampleBlock({
        ...test, name: test.name + (test.visibility === "hidden" ? "（隐藏）" : "（公开）"),
      })));
    }
    const stats = state.caseStats.map((test) => {
      const evaluated = test.passed + test.failed;
      const rate = evaluated ? "通过率 " + Math.round(100 * test.passed / evaluated) + "%" : "暂无用例结果";
      const title = test.name + (test.visibility === "hidden" ? "（隐藏）" : "（公开）");
      return element("li", title + " · " + test.passed + " 通过 / " + test.failed + " 失败 · " + rate);
    });
    byId("case-stats").replaceChildren(...stats);
    byId("no-errors").hidden = state.errorGroups.length > 0;
    const groups = state.errorGroups.map((group) => {
      const item = element("li");
      item.append(element("strong", (categoryText[group.category] || "其他编译诊断") + " · " + group.count + " 人"));
      if (group.example) item.append(element("pre", group.example));
      item.append(detailButton(group.studentNumber, state.task.id));
      return item;
    });
    byId("error-groups").replaceChildren(...groups);
  }

  function showDashboard() {
    link.value = new URL("/join/" + credentials.id, location.origin).href;
    byId("setup").hidden = true;
    byId("dashboard").hidden = false;
    try {
      const qr = joinQr(link.value);
      qrButton.replaceChildren(qr);
      byId("qr-large").replaceChildren(qr.cloneNode(true));
      byId("share-hint").textContent = "扫描二维码或打开链接即可进入学生页面。点击二维码可放大投影。";
      qrButton.hidden = false;
    } catch {
      qrButton.hidden = true;
      byId("share-hint").textContent = "二维码暂不可用，请复制加入链接。";
    }
  }

  function refreshStatus(message) {
    const status = byId("refresh-state");
    if (status.textContent !== message) status.textContent = message;
  }

  function showProgress(state) {
    byId("room-name").textContent = state.name;
    byId("current-task").textContent = state.task ? "当前任务 · " + state.task.title : "尚未发布任务";
    for (const key of ["joined", "submitted", "attempts", "unsubmitted", "accepted", "failed", "queued", "pending", "unjudged"]) {
      byId(key).textContent = state[key];
    }
    byId("judge-state").textContent = state.executionAvailable ? "" :
      (state.queued ? "评测器暂不可用，等待中的提交已保存，连接恢复后继续。" : "隔离执行器不可用，未评测的提交不会计为未通过。");
    const judged = state.accepted + state.failed;
    byId("class-pass-rate").textContent = judged ?
      "最新提交通过率 " + Math.round(100 * state.accepted / judged) + "%（覆盖 " + judged + " 人）" :
      "暂无已完成的评测，暂不计算通过率。";
    refreshStatus("每 2 秒更新");
    byId("empty-students").hidden = state.students.length > 0;
    const signature = JSON.stringify([state.task?.id, state.students, state.caseStats, state.errorGroups]);
    if (signature === analysisSignature) return;
    analysisSignature = signature;
    renderAnalysis(state);
    const rows = state.students.map((student) => {
      const row = document.createElement("tr");
      const status = state.task ? (student.count ? statusText[student.latestStatus] || "结果未知" : "未提交") : "等待任务";
      const score = student.total === undefined ? "" : " · " + student.passed + "/" + student.total;
      row.insertCell().textContent = student.name + " #" + student.number;
      const statusCell = row.insertCell();
      statusCell.textContent = status + score;
      statusCell.classList.toggle("status-received", ["received", "accepted"].includes(student.latestStatus));
      row.insertCell().textContent = student.count;
      const detail = row.insertCell();
      if (student.count) detail.append(detailButton(student.number, state.task.id));
      return row;
    });
    byId("students").replaceChildren(...rows);
  }

  const refresh = poll(async () => {
    if (credentials) showProgress(await api(endpoint("/progress"), { headers: headers() }));
  }, (error) => {
    if (error.status === 403 || error.status === 404) {
      localStorage.removeItem(storageKey);
      credentials = null;
      byId("setup").hidden = false;
      if (qrDialog.open) qrDialog.close();
      if (submissionDialog.open) submissionDialog.close();
      byId("dashboard").hidden = true;
      feedback(error.message, true);
    } else {
      refreshStatus("连接中断，数值可能过时");
    }
  });

  onSubmit("create", async (data) => {
    credentials = await api("/rooms", { data });
    localStorage.setItem(storageKey, JSON.stringify(credentials));
    byId("room-name").textContent = data.name;
    showDashboard();
    await refresh();
  });

  onSubmit("publish", async (data) => {
    const cases = Array.from(caseRows.children, (row) => Object.fromEntries(
      Array.from(row.querySelectorAll("[data-field]"), (field) => [field.dataset.field, field.value])
    ));
    if (cases.length) data.testCases = cases;
    await api(endpoint("/tasks"), { data, headers: headers() });
    byId("publish").reset();
    caseRows.replaceChildren();
    addCase.disabled = false;
    feedback("任务已发布。", false, "publish-feedback");
    await refresh();
  }, "publish-feedback");

  byId("copy-link").addEventListener("click", () => copyText(link, "copy-feedback", "加入链接已复制。"));
  qrButton.addEventListener("click", () => qrDialog.showModal());

  if (credentials) {
    showDashboard();
    void refresh();
  }
}

function initializeStudent() {
  const room = location.pathname.split("/").pop();
  const storageKey = "classlab.student." + room;
  let key = localStorage.getItem(storageKey);
  let currentTask = null;
  let resultSignature;
  let pendingSubmission;
  let running = false;
  const editor = byId("submit").elements.code;
  const endpoint = (suffix) => "/rooms/" + room + suffix;
  const headers = () => ({ "X-Student-Key": key });
  const draftKey = (id) => storageKey + ".draft." + id;

  function showTask(state) {
    byId("setup").hidden = true;
    byId("workspace").hidden = false;
    byId("connection").textContent = "";
    feedback("");
    byId("room-name").textContent = state.roomName;
    byId("student-name").textContent = state.studentName;
    byId("waiting").hidden = Boolean(state.task);
    byId("assignment").hidden = !state.task;
    byId("run-controls").disabled = !state.executionAvailable || running;
    const runStatus = byId("run-state");
    const runMessage = running ? "正在编译和运行…" : (state.executionAvailable ?
      "自由运行使用自定义输入，不计入正式提交。" : "隔离执行器不可用，暂时无法运行代码。");
    if (runStatus.textContent !== runMessage) runStatus.textContent = runMessage;
    const signature = JSON.stringify([state.task?.id, state.latestResult]);
    if (signature !== resultSignature) {
      resultSignature = signature;
      byId("latest-result").hidden = !state.latestResult;
      displayResult(byId("student-result"), state.latestResult);
    }
    if (!state.task || state.task.id === currentTask?.id) return;
    feedback("", false, "submit-feedback");
    byId("run-result").hidden = true;
    byId("editor-feedback").textContent = currentTask ? "教师已发布新任务。" : "";
    currentTask = state.task;
    byId("task-title").textContent = currentTask.title;
    byId("task-description").textContent = currentTask.description;
    const tests = currentTask.testCases || [];
    byId("public-tests").hidden = !tests.length;
    byId("public-tests").open = false;
    byId("student-public-tests").replaceChildren(...tests.map(sampleBlock));
    editor.value = localStorage.getItem(draftKey(currentTask.id)) ?? currentTask.starterCode;
  }

  const refresh = poll(async () => {
    if (key) showTask(await api(endpoint("/task"), { headers: headers() }));
  }, (error) => {
    if (error.status === 403 || error.status === 404) {
      localStorage.removeItem(storageKey);
      key = null;
      currentTask = null;
      byId("setup").hidden = false;
      byId("workspace").hidden = true;
      feedback(error.message, true);
    } else {
      const target = byId("workspace").hidden ? "feedback" : "connection";
      feedback("任务刷新失败，系统正在重试。", true, target);
    }
  });

  onSubmit("join", async (data) => {
    const result = await api(endpoint("/students"), { data });
    key = result.studentKey;
    localStorage.setItem(storageKey, key);
    await refresh();
  });

  byId("copy-code").addEventListener("click", () => copyText(editor, "editor-feedback", "代码已复制。"));
  editor.addEventListener("input", () => {
    if (!currentTask) return;
    try {
      localStorage.setItem(draftKey(currentTask.id), editor.value);
      byId("editor-feedback").textContent = "草稿已保存在此浏览器。";
    } catch {
      byId("editor-feedback").textContent = "草稿无法保存，请在刷新前复制代码。";
    }
  });

  byId("run-code").addEventListener("click", async () => {
    if (running || !currentTask || !editor.reportValidity()) return;
    const taskId = currentTask.id;
    const panel = byId("run-result");
    const input = byId("submit").elements.runInput.value;
    running = true;
    byId("run-controls").disabled = true;
    byId("run-state").textContent = "正在编译和运行…";
    panel.hidden = true;
    try {
      const result = await api(endpoint("/run"), { headers: headers(), timeoutMs: 115000,
        data: { taskId, code: editor.value, input } });
      if (taskId !== currentTask?.id) return;
      displayResult(panel, result);
      if (Object.hasOwn(result, "exitCode")) panel.append(element("p", "退出状态 " + result.exitCode));
      if (Object.hasOwn(result, "stdout")) panel.append(element("strong", "标准输出"), element("pre", result.stdout || "（空）"));
      if (result.stderr) panel.append(element("strong", "标准错误"), element("pre", result.stderr));
      panel.hidden = false;
    } catch (error) {
      if (taskId === currentTask?.id) {
        panel.replaceChildren(element("p", error.message));
        panel.hidden = false;
      }
    } finally {
      running = false;
      await refresh();
    }
  });

  onSubmit("submit", async ({ code }) => {
    const taskId = currentTask.id;
    try {
      if (pendingSubmission?.taskId !== taskId || pendingSubmission.code !== code) {
        const requestId = [...crypto.getRandomValues(new Uint8Array(16))]
          .map((byte) => byte.toString(16).padStart(2, "0")).join("");
        pendingSubmission = { taskId, code, requestId };
      }
      feedback("正在保存代码…", false, "submit-feedback");
      const receipt = await api(endpoint("/submissions"), { data: pendingSubmission, headers: headers() });
      pendingSubmission = null;
      if (taskId === currentTask?.id) {
        const message = receipt.judgement === "judge_unavailable" ?
          "代码已保存。隔离执行器不可用，本次提交未评测。" :
          receipt.judgement === "queued" || receipt.judgement === "pending" ?
            "代码已保存，评测进度见下方。" :
          receipt.judgement === "judge_queue_full" ?
            "代码已保存，但评测队列已满。稍后可再次提交。" :
          receipt.judgement ? "代码已保存 · " + (statusText[receipt.judgement] || "状态未知") :
            "代码已提交，教师可以看到收件状态。";
        feedback(message, false, "submit-feedback");
        await refresh();
      }
    } catch (error) {
      if (error.status === 409) await refresh();
      throw error;
    }
  }, "submit-feedback");

  if (key) void refresh();
}

if (document.body.dataset.view === "teacher") initializeTeacher();
else initializeStudent();
