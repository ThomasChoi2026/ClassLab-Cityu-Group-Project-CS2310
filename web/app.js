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
  try {
    response = await fetch("/api" + path, data === undefined ? { headers } : {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  } catch {
    throw new RequestError("连接中断，请稍后重试。", 0);
  }
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new RequestError(result.error || "请求失败。", response.status);
  return result;
}

function feedback(message, error = false) {
  const node = byId("feedback");
  node.textContent = message;
  node.classList.toggle("error", error);
}

function onSubmit(id, action) {
  byId(id).addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector("button");
    button.disabled = true;
    feedback("");
    try {
      await action(Object.fromEntries(new FormData(form)));
    } catch (error) {
      feedback(error.message, true);
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

function initializeTeacher() {
  const storageKey = "classlab.teacher";
  let credentials = JSON.parse(localStorage.getItem(storageKey) || "null");
  const headers = () => ({ "X-Teacher-Key": credentials.teacherKey });
  const endpoint = (suffix) => "/rooms/" + credentials.id + suffix;
  const link = byId("join-link");

  function showDashboard() {
    link.value = new URL("/join/" + credentials.id, location.origin).href;
    byId("setup").hidden = true;
    byId("dashboard").hidden = false;
  }

  function showProgress(state) {
    byId("room-name").textContent = state.name;
    byId("current-task").textContent = state.task ? "当前任务 · " + state.task.title : "尚未发布任务";
    byId("joined").textContent = state.joined;
    byId("submitted").textContent = state.submitted;
    byId("attempts").textContent = state.attempts;
    byId("refresh-state").textContent = "每 2 秒刷新";
    byId("empty-students").hidden = state.students.length > 0;
    const rows = state.students.map((student) => {
      const row = document.createElement("tr");
      const status = state.task ? (student.count ? "已提交" : "未提交") : "等待任务";
      for (const value of [student.name + " #" + student.number, status, student.count]) {
        row.insertCell().textContent = value;
      }
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
      byId("dashboard").hidden = true;
      feedback(error.message, true);
    } else {
      byId("refresh-state").textContent = "刷新失败，正在重试";
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
    feedback("任务已发布。");
    await refresh();
  });

  byId("copy-link").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(link.value);
      feedback("加入链接已复制。");
    } catch {
      link.select();
      feedback("已选中链接，请使用复制快捷键。");
    }
  });

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
    byId("room-name").textContent = state.roomName;
    byId("student-name").textContent = state.studentName;
    byId("waiting").hidden = Boolean(state.task);
    byId("assignment").hidden = !state.task;
    if (!state.task || state.task.id === currentTask?.id) return;
    if (currentTask) feedback("教师已发布新任务，上一题草稿已保留在此浏览器。");
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
    }
    feedback(error.message, true);
  });

  onSubmit("join", async (data) => {
    const result = await api(endpoint("/students"), { data });
    key = result.studentKey;
    localStorage.setItem(storageKey, key);
    await refresh();
  });

  editor.addEventListener("input", () => {
    if (currentTask) localStorage.setItem(draftKey(currentTask.id), editor.value);
  });

  onSubmit("submit", async ({ code }) => {
    const taskId = currentTask.id;
    try {
      await api(endpoint("/submissions"), { data: { taskId, code }, headers: headers() });
      if (taskId === currentTask?.id) feedback("代码已提交，教师可以看到收件状态。");
    } catch (error) {
      if (error.status === 409) await refresh();
      throw error;
    }
  });

  if (key) void refresh();
}

if (document.body.dataset.view === "teacher") initializeTeacher();
else initializeStudent();
