"use strict";

const byId = (id) => document.getElementById(id);
const interval = 2000;

class RequestError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function api(path, { data, headers = {} } = {}) {
  let response;
  let result;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
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

function initializeTeacher() {
  const storageKey = "classlab.teacher";
  let credentials = JSON.parse(localStorage.getItem(storageKey) || "null");
  const headers = () => ({ "X-Teacher-Key": credentials.teacherKey });
  const endpoint = (suffix) => "/rooms/" + credentials.id + suffix;
  const link = byId("join-link");
  const qrButton = byId("show-qr");
  const qrDialog = byId("qr-dialog");

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
    byId("joined").textContent = state.joined;
    byId("submitted").textContent = state.submitted;
    byId("attempts").textContent = state.attempts;
    refreshStatus("每 2 秒更新");
    byId("empty-students").hidden = state.students.length > 0;
    const rows = state.students.map((student) => {
      const row = document.createElement("tr");
      const status = state.task ? (student.count ? "已提交" : "未提交") : "等待任务";
      row.insertCell().textContent = student.name + " #" + student.number;
      const statusCell = row.insertCell();
      statusCell.textContent = status;
      statusCell.classList.toggle("status-received", student.count > 0);
      row.insertCell().textContent = student.count;
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
    await api(endpoint("/tasks"), { data, headers: headers() });
    byId("publish").reset();
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
    if (!state.task || state.task.id === currentTask?.id) return;
    feedback("", false, "submit-feedback");
    byId("editor-feedback").textContent = currentTask ? "教师已发布新任务。" : "";
    currentTask = state.task;
    byId("task-title").textContent = currentTask.title;
    byId("task-description").textContent = currentTask.description;
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

  onSubmit("submit", async ({ code }) => {
    const taskId = currentTask.id;
    try {
      await api(endpoint("/submissions"), { data: { taskId, code }, headers: headers() });
      if (taskId === currentTask?.id) feedback("代码已提交，教师可以看到收件状态。", false, "submit-feedback");
    } catch (error) {
      if (error.status === 409) await refresh();
      throw error;
    }
  }, "submit-feedback");

  if (key) void refresh();
}

if (document.body.dataset.view === "teacher") initializeTeacher();
else initializeStudent();
