
"use strict";

const byId = (id) => document.getElementById(id);
const interval = 2000;

class RequestError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function api(path, { data, headers = {}, timeoutMs = 8000, method = data === undefined ? "GET" : "POST" } = {}) {
  let response;
  let result;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const { signal } = controller;
  try {
    response = await fetch("/api" + path, data === undefined ? { method, headers, signal } : {
      signal,
      method,
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
    return true;
  } catch {
    field.focus();
    field.select();
    byId(status).textContent = "已选中文本，请使用浏览器的复制操作。";
    return false;
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
  compiling: "正在编译",
  running: "运行中",
  stopping: "正在停止",
  stopped: "已停止",
  idle_timeout: "输入/输出等待超时",
  busy: "运行资源正忙",
  not_found: "运行会话已结束",
  request_error: "请求错误",
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

function csvCell(value) {
  const text = value === null || value === undefined ? "" : String(value);
  // Prefix formula-like text before CSV quoting so Excel treats it as literal data.
  const safe = /^[\s\uFEFF]*[=+\-@]/u.test(text) ? "'" + text : text;
  return '"' + safe.replace(/"/g, '""') + '"';
}

function exportedStatus(status, count) {
  if (!count) return "Not submitted";
  const labels = {
    received: "Submitted (not evaluated)",
    queued: "Waiting for evaluation",
    pending: "Evaluating",
    judge_unavailable: "Not evaluated (Judge unavailable)",
    judge_queue_full: "Not evaluated (evaluation queue full)",
    judge_error: "Evaluation service error",
    accepted: "All tests passed",
    wrong_answer: "Tests not all passed (wrong answer)",
    compilation_error: "Compilation error",
    runtime_error: "Runtime error",
    time_limit: "Time limit exceeded",
    resource_limit: "Resource limit exceeded",
  };
  return labels[status] || (status ? "Unknown status (" + status + ")" : "Submitted (status unavailable)");
}

function buildClassroomCsv(state, exportedAt = new Date()) {
  const headers = [
    "Classroom Name", "Task Title", "Student Number", "Student Name",
    "Submission Count", "Latest Submission Status", "Passed Test Cases",
    "Total Test Cases", "Mode", "Exported At (UTC)"
  ];
  const exportedAtUtc = exportedAt.toISOString();
  const rows = state.students.map(student => {
    const hasScore = Number.isFinite(student.passed) && Number.isFinite(student.total);
    return [
      state.name,
      state.task.title,
      student.number,
      student.name,
      Number.isFinite(student.count) ? student.count : "",
      exportedStatus(student.latestStatus, student.count),
      hasScore ? student.passed : "",
      hasScore ? student.total : "",
      "Normal",
      exportedAtUtc,
    ].map(csvCell).join(",");
  });
  return "\uFEFF" + [headers.map(csvCell).join(","), ...rows].join("\r\n") + "\r\n";
}

function safeFilePart(value) {
  return String(value || "ClassLab")
    .replace(/[<>:"/\\|?*\x00-\x1F]/g, "-")
    .replace(/\s+/g, "-")
    .slice(0, 70) || "ClassLab";
}

function runResultCopyText(result) {
  const sections = [];
  if (result.demoFixture) {
    sections.push("DEMO REPLAY — 预置演示回放；没有编译或执行当前 C++ 代码。");
  }
  if (result.status) {
    sections.push("运行状态：" + (statusText[result.status] || result.status));
  }
  if (result.error) sections.push("运行错误：\n" + String(result.error));
  if (result.diagnostic) sections.push("编译诊断：\n" + String(result.diagnostic));
  if (Object.hasOwn(result, "stdout")) {
    sections.push("标准输出：\n" + String(result.stdout ?? ""));
  }
  if (Object.hasOwn(result, "stderr")) {
    sections.push("标准错误：\n" + String(result.stderr ?? ""));
  }
  if (Object.hasOwn(result, "exitCode")) {
    sections.push("退出状态：" + String(result.exitCode));
  }
  return sections.length ? sections.join("\n\n") : "运行结果：没有可复制的输出。";
}

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

function scheduleView(onRemove) {
  const days = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"];
  let signature;
  return (slots) => {
    const next = JSON.stringify(slots);
    if (signature === next) return;
    signature = next;
    byId("schedule-empty").hidden = slots.length > 0;
    byId("schedule-list").replaceChildren(...slots.map(slot => {
      const label = days[slot.day - 1] + " " + slot.start + "–" + slot.end;
      const row = element("li");
      row.append(element("strong", slot.name), element("span", label));
      if (onRemove) {
        const remove = element("button", "移除");
        remove.type = "button";
        remove.className = "secondary";
        remove.setAttribute("aria-label", "移除 " + slot.name + " " + label);
        remove.addEventListener("click", async () => {
          remove.disabled = true;
          try {
            await onRemove(slot);
          } catch (error) {
            feedback(error.message, true, "schedule-feedback");
          } finally {
            remove.disabled = false;
          }
        });
        row.append(remove);
      }
      return row;
    }));
  };
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

function displayResult(container, result, teacherCases) {
  container.replaceChildren();
  if (!result) return;
  const score = result.total === undefined ? "" : " · " + result.passed + "/" + result.total + " 通过";
  container.append(element("p", (statusText[result.status] || "结果未知") + score));
  if (result.demoFixture) container.append(element("p", "预置演示回放：没有编译或执行当前 C++ 代码。"));
  if (result.diagnostic) container.append(element("pre", result.diagnostic));
  if (teacherCases) {
    for (const test of result.cases || []) {
      const config = teacherCases.find(item => item.id === test.testId);
      const name = config ? config.name + (config.visibility === "hidden" ? "（隐藏）" : "") : "用例 " + test.testId;
      const details = element("details");
      details.append(element("summary", name + " · " + (statusText[test.status] || "结果未知")),
        sampleBlock({...config, ...test, name}));
      container.append(details);
    }
  } else {
    for (const test of result.cases || []) container.append(sampleBlock(test));
  }
}

function initializeNotebookImport(form, loadExercise) {
  const picker = byId("notebook-file");
  const list = byId("notebook-list");
  const search = byId("notebook-search");
  const filter = byId("notebook-filter");
  const currentLabel = byId("notebook-current-label");
  const status = byId("notebook-status");
  const preview = byId("notebook-preview");
  const fields = byId("notebook-cells");
  const overview = byId("notebook-overview");
  const use = byId("use-notebook-cell");
  const toggleCell = byId("toggle-prep-cell");
  const combination = byId("notebook-combination");
  const combinationSummary = combination.querySelector("summary");
  const assemble = byId("assemble-notebook");
  const appendText = byId("append-notebook-text");
  const selection = byId("selected-prep-cells");
  const selected = new Set();
  let selectionApplied = false;
  let cells = [];
  let current = 0;
  let version = 0;

  function kindOf(cell) {
    if (cell.kind === "markdown") return "markdown";
    const source = cell.code.trimStart();
    const magic = source.match(/^%%([\w-]+)/)?.[1]?.toLowerCase();
    if (magic) return magic === "cpp" && /^%%cpp[ \t]*(?:\r?\n|$)/.test(source) ? "cpp" : "other";
    if (/^(?:from\s+\S+\s+import\s+|import\s+\w+|def\s+\w+\s*\()/m.test(source)) return "other";
    return /(?:#\s*include\s*[<"]|\bstd::|\b(?:int\s+main|class|struct|template|constexpr|using\s+namespace)\b)/.test(source)
      ? "cpp" : "other";
  }

  function summaryOf(cell) {
    const lines = cell.code.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    return (lines.find(line => !/^(?:%%|#\s*include\b|using\s+namespace\b)/.test(line)) || lines[0] || "（空单元）").slice(0, 100);
  }

  function showSelection() {
    const numbers = cells.filter((_, position) => selected.has(position)).map(cell => cell.index + 1);
    selection.textContent = numbers.length
      ? "组合 Cell " + numbers.join(" → ") + (selectionApplied ? " 已填入起始代码。" : " 尚未填入起始代码。")
      : "尚未选择组合单元。";
    assemble.disabled = !numbers.length;
    combination.hidden = !numbers.length && (!cells[current] || toggleCell.hidden);
    combinationSummary.textContent = "多 Cell 组合（高级）" + (numbers.length
      ? " · " + numbers.length + (selectionApplied ? " 个已填入" : " 个待填入") : "");
  }

  function matchingCells() {
    const term = search.value.trim().toLowerCase();
    const selectedType = filter.value;
    return cells.map((cell, position) => ({cell, position})).filter(({cell}) => {
      const typeMatches = selectedType === "all" || (selectedType === "exercise" ? Boolean(cell.exercise) : kindOf(cell) === selectedType);
      const searchMatches = !term || String(cell.index + 1).includes(term) || cell.code.toLowerCase().includes(term) || (cell.exercise?.title || "").toLowerCase().includes(term);
      return typeMatches && searchMatches;
    });
  }

  function renderList() {
    const entries = matchingCells().map(({cell, position}) => {
      const label = cell.exercise ? "课堂互动练习" : cell.protected ? "仅教师预览 / 不可载入" : kindOf(cell) === "cpp" ? "C++" : kindOf(cell) === "markdown" ? "Markdown" : "其他代码";
      const button = element("button");
      const meta = element("span", "Cell " + (cell.index + 1) +
        (cell.exercise && filter.value === "exercise" ? "" : " · " + label) + " ");
      meta.className = "notebook-cell-meta";
      const title = element("span", cell.exercise?.title || summaryOf(cell));
      title.className = "notebook-cell-title";
      button.append(meta, title);
      button.type = "button";
      button.className = "notebook-cell-entry" + (position === current ? " active" : "");
      button.setAttribute("aria-pressed", String(position === current));
      if (selected.has(position)) {
        button.classList.add("chosen");
        meta.textContent += " · 已选入组合";
      }
      button.addEventListener("click", () => {
        current = position;
        showCell();
        if (cell.exercise) importExercise(cell);
      });
      return button;
    });
    list.replaceChildren(...entries);
    if (!entries.length) list.append(element("p", "没有匹配的单元，可修改搜索或筛选条件。"));
  }

  function showCell() {
    const cell = cells[current];
    if (!cell) return;
    currentLabel.textContent = "Cell " + (cell.index + 1) + " · " +
      (cell.exercise ? cell.exercise.title : cell.protected ? "教师专用 / 无效互动信息" : kindOf(cell) === "cpp" ? "C++ 代码" : kindOf(cell) === "markdown" ? "Markdown" : "其他代码");
    preview.textContent = cell.code;
    const isCode = cell.kind === "code";
    use.hidden = !isCode || cell.protected;
    use.textContent = cell.exercise ? "载入互动练习" : "用此 Cell 作为起始代码";
    toggleCell.hidden = !isCode || cell.protected || Boolean(cell.exercise);
    appendText.hidden = isCode || cell.protected;
    toggleCell.textContent = selected.has(current) ? "从组合移除" : "加入代码组合";
    toggleCell.setAttribute("aria-pressed", String(selected.has(current)));
    status.textContent = cell.warning || (cell.exercise
      ? "互动练习含 " + cell.exercise.testCases.length + " 个用例；载入后请检查再发布。"
      : isCode ? preparedSource(cell).error || "这里只是预览。请使用此 Cell 或将它加入组合。"
        : "这里只是预览。可将此 Cell 追加到任务说明。");
    showSelection();
    renderList();
  }

  function clear() {
    ++version;
    cells = [];
    current = 0;
    selected.clear();
    selectionApplied = false;
    combination.open = false;
    combination.hidden = true;
    search.value = "";
    filter.value = "all";
    list.replaceChildren();
    preview.textContent = "";
    currentLabel.textContent = "";
    fields.hidden = true;
    overview.hidden = true;
    overview.textContent = "";
    status.textContent = "";
    showSelection();
  }

  function preparedSource(cell) {
    if (!cell || cell.kind !== "code") return {error: "只能将代码单元放入 C++ 起始代码。"};
    if (cell.protected) return {error: cell.warning};
    if (cell.exercise) return {error: "互动练习请独立载入，避免混合代码和测试规格。"};
    let code = cell.code;
    const notes = [];
    const magic = code.match(/^\s*%%([\w-]+)[^\r\n]*(?:\r?\n|$)/);
    if (magic) {
      const name = magic[1].toLowerCase();
      if (name === "cpp" && !/^\s*%%cpp[ \t]*(?:\r?\n|$)/.test(code)) return {error: "Cell " + (cell.index + 1) + " 仅支持无参数的 %%cpp；请手动整理。"};
      if (name !== "cpp") return {error: "Cell " + (cell.index + 1) +
        " 使用 %%" + name + "，不是标准 C++；请在预览中核对并手动转换。"};
      code = code.slice(magic[0].length);
      notes.push("Cell " + (cell.index + 1) + "：已移除 %%cpp 魔法指令，请检查生成的 C++。");
    }
    if (/^\s*(?:from\s+\S+\s+import\s+|import\s+\w+|def\s+\w+\s*\()/m.test(code)) {
      return {error: "Cell " + (cell.index + 1) + " 疑似 Python 代码，不会作为 C++ 起始代码插入。"};
    }
    if (/(?:^|\n)\s*[%!](?![%=])/.test(code)) {
      return {error: "Cell " + (cell.index + 1) + " 包含未处理的 Notebook 指令，请手动转换。"};
    }
    if (!code.trim()) return {error: "Cell " + (cell.index + 1) + " 没有可加入的 C++ 代码。"};
    return {code, notes};
  }

  function fillCode(code, source, notes) {
    if (code.length > 20000 || new TextEncoder().encode(code).length > 65536) {
      status.textContent = "所选代码超过起始代码长度限制。";
      return false;
    }
    const mainCount = (code.match(/\bmain\s*\(/g) || []).length;
    if (mainCount === 0) notes.push("未发现 main()：代码可能只是定义或片段，请补齐入口和依赖。");
    if (mainCount > 1) notes.push("检测到多个 main()：请保留一个入口并手动整理。");
    form.elements.starterCode.value = code;
    form.elements.starterCode.dispatchEvent(new Event("input"));
    status.textContent = [source + " 已填入起始代码。", ...notes].join(" ");
    return true;
  }

  picker.addEventListener("change", async () => {
    clear();
    const file = picker.files[0];
    if (!file) return;
    const readVersion = version;
    if (!file.name.toLowerCase().endsWith(".ipynb") || file.size > 2 * 1024 * 1024) {
      status.textContent = "请选择不超过 2 MiB 的 .ipynb 文件。";
      return;
    }
    try {
      const notebook = JSON.parse(await file.text());
      if (readVersion !== version) return;
      const parsed = ClassLabNotebook.parse(notebook);
      cells = parsed.cells;
      overview.textContent = file.name + " · 总 Cell：" + parsed.total + " · 课堂互动练习：" + parsed.count + (parsed.warnings ? " · 需检查：" + parsed.warnings : "");
      overview.hidden = false;
      if (parsed.count) {
        filter.value = "exercise";
        current = cells.findIndex(cell => cell.exercise);
      }
      if (!cells.length) {
        status.textContent = "此 Notebook 没有可读取的代码或 Markdown 单元。";
        return;
      }
      fields.hidden = false;
      showCell();
      showSelection();
    } catch {
      if (readVersion === version) status.textContent = "无法读取此文件，请选择有效的 Notebook v4。";
    }
  });

  function refreshFilter() {
    const matches = matchingCells();
    if (matches.some(entry => entry.position === current)) {
      renderList();
    } else if (matches.length) {
      current = matches[0].position;
      showCell(); // Preview only, never load or publish on filtering.
    } else {
      current = -1;
      currentLabel.textContent = "没有匹配的单元";
      preview.textContent = "";
      use.hidden = toggleCell.hidden = appendText.hidden = true;
      showSelection();
      status.textContent = "没有匹配的单元，可修改搜索或筛选条件。";
      renderList();
    }
  }

  search.addEventListener("input", refreshFilter);
  // Enter in cell search must never submit or publish the teacher form.
  search.addEventListener("keydown", event => {
    if (event.key === "Enter") event.preventDefault();
  });
  filter.addEventListener("change", refreshFilter);
  function importExercise(cell) {
    if (!cell?.exercise || cell.protected) return;
    if (!loadExercise(cell.exercise)) {
      status.textContent = "保留了当前编辑内容；可点击载入互动练习再次选择。";
      return;
    }
    resetSelection();
    status.textContent = "已载入互动练习，尚未发布。请核对说明和用例。" + (cell.warning ? " " + cell.warning : "");
  }
  use.addEventListener("click", () => {
    if (cells[current]?.exercise) return importExercise(cells[current]);
    const result = preparedSource(cells[current]);
    if (result.error) return void (status.textContent = result.error);
    if (fillCode(result.code, "Cell " + (cells[current].index + 1), result.notes)) {
      resetSelection();
    }
  });
  toggleCell.addEventListener("click", () => {
    if (!selected.delete(current)) {
      const result = preparedSource(cells[current]);
      if (result.error) return void (status.textContent = result.error);
      selected.add(current);
    }
    selectionApplied = false;
    showCell();
  });
  assemble.addEventListener("click", () => {
    const parts = [], notes = [];
    for (const [position, cell] of cells.entries()) {
      if (!selected.has(position)) continue;
      const result = preparedSource(cell);
      if (result.error) return void (status.textContent = result.error);
      parts.push(result.code.trimEnd());
      notes.push(...result.notes);
    }
    if (parts.length && fillCode(parts.join("\n\n"), "所选组合", notes)) {
      selectionApplied = true;
      showSelection();
    }
  });
  appendText.addEventListener("click", () => {
    if (!cells[current] || cells[current].kind !== "markdown" || cells[current].protected) return;
    const field = form.elements.description;
    const next = [field.value, cells[current].code.trim()].filter(Boolean).join("\n\n");
    if (next.length > field.maxLength || new TextEncoder().encode(next).length > 10000) {
      status.textContent = "追加后说明过长，请在预览中复制需要的部分。";
      return;
    }
    field.value = next;
    status.textContent = "Markdown 已追加为纯文字，可继续修改。";
  });
  function resetSelection() {
    selected.clear();
    selectionApplied = false;
    if (cells.length) renderList();
    showSelection();
    toggleCell.textContent = "加入代码组合";
    toggleCell.setAttribute("aria-pressed", "false");
  }

  return {
    hasPendingSelection: () => selected.size > 0 && !selectionApplied,
    resetSelection,
    finishTask() {
      if (!cells.length) return;
      resetSelection();
      combination.open = false;
      status.textContent = "已保留 Notebook，可继续浏览并准备下一题。";
    },
  };
}

function renderDiff(original, code) {
  const panel = byId("submission-diff");
  const full = byId("full-source");
  panel.replaceChildren();
  byId("starter-code").textContent = original;
  byId("submission-code").textContent = code;
  const rows = compareLines(original, code);
  full.open = rows === null;
  const added = rows?.filter(row => row.kind === "+").length || 0;
  const removed = rows?.filter(row => row.kind === "-").length || 0;
  panel.hidden = !added && !removed;
  byId("diff-summary").textContent = rows === null ? "改动范围较大，请对照下方两份完整源码。" :
    panel.hidden ? "与起始代码逐行相同（统一换行格式）。" :
    "新增 " + added + " 行，删除 " + removed + " 行。左列为原行号，右列为新行号。";
  if (panel.hidden) return;
  // Show two context rows on either side. Group adjoining rows for large pastes.
  let chunk = "", lastKind, skipped = false;
  function flush() {
    if (!chunk) return;
    const span = element("span", chunk);
    span.className = lastKind === "+" ? "diff-add" : lastKind === "-" ? "diff-del" : "";
    panel.append(span);
    chunk = "";
  }
  rows.forEach((row, index) => {
    const visible = row.kind !== " " || rows.slice(Math.max(0, index - 2), index + 3).some(r => r.kind !== " ");
    if (!visible) {
      if (!skipped) { flush(); panel.append(document.createTextNode("…\n")); }
      skipped = true;
      return;
    }
    skipped = false;
    if (row.kind !== lastKind) flush();
    lastKind = row.kind;
    chunk += String(row.old ?? "").padStart(5) + " " + String(row.next ?? "").padStart(5) +
      "  " + row.kind + " " + row.text + "\n";
  });
  flush();
}

function initializeLessonLibrary(serialize, load) {
  const key = "classlab.lesson-drafts.v1";
  const picker = byId("draft-library");
  const open = byId("load-draft");
  const remove = byId("delete-draft");
  const update = byId("update-draft");
  let loaded;

  function drafts() {
    try {
      const values = JSON.parse(localStorage.getItem(key) || "[]");
      if (Array.isArray(values)) return values;
    } catch {}
    feedback("无法读取备课草稿。", true, "draft-feedback");
    return [];
  }

  function render(id = "") {
    const options = drafts().map(draft => {
      const option = element("option", draft.lesson.title);
      option.value = draft.id;
      return option;
    });
    picker.replaceChildren(element("option", "选择练习"), ...options);
    picker.firstElementChild.value = "";
    picker.value = id;
    if (!picker.value) picker.value = "";
    open.disabled = remove.disabled = !picker.value;
    update.hidden = !loaded;
  }

  function save(id) {
    const lesson = serialize();
    if (!lesson.title.trim()) {
      feedback("请填写练习标题后保存。", true, "draft-feedback");
      return;
    }
    const values = drafts();
    const existing = id && values.find(draft => draft.id === id);
    if (id && !existing) {
      feedback("这份草稿已删除，可另存为新练习。", true, "draft-feedback");
      return;
    }
    if (!existing && values.some(draft => draft.lesson.title.trim().toLowerCase() === lesson.title.trim().toLowerCase())) {
      feedback("已有同名练习，请更改名称后保存。", true, "draft-feedback");
      return;
    }
    if (!existing && values.length >= 25) {
      feedback("练习库最多保留 25 份草稿。", true, "draft-feedback");
      return;
    }
    const record = existing || { id: String(Date.now()) + "-" + Math.random().toString(36).slice(2) };
    record.lesson = lesson;
    if (!existing) values.push(record);
    try {
      localStorage.setItem(key, JSON.stringify(values));
      loaded = record.id;
      render(loaded);
      feedback("练习已保存到当前浏览器。", false, "draft-feedback");
    } catch {
      feedback("无法写入浏览器存储，编辑器内容仍可复制。", true, "draft-feedback");
    }
  }

  picker.addEventListener("change", () => { open.disabled = remove.disabled = !picker.value; });
  byId("save-draft").addEventListener("click", () => save());
  update.addEventListener("click", () => save(loaded));
  open.addEventListener("click", () => {
    const record = drafts().find(draft => draft.id === picker.value);
    if (!record) return render();
    load(record.lesson);
    loaded = record.id;
    render(loaded);
    feedback("练习已载入，可修改或发布。", false, "draft-feedback");
  });
  remove.addEventListener("click", () => {
    if (!confirm("删除所选的本地备课草稿？")) return;
    const id = picker.value;
    try {
      localStorage.setItem(key, JSON.stringify(drafts().filter(draft => draft.id !== id)));
      if (loaded === id) loaded = undefined;
      render();
      feedback("草稿已删除。", false, "draft-feedback");
    } catch {
      feedback("无法删除草稿。", true, "draft-feedback");
    }
  });
  render();
  return () => { loaded = undefined; render(); };
}

function taskPicker(select, container) {
  let lastOptions;
  return (tasks = []) => {
    const options = JSON.stringify(tasks);
    if (options === lastOptions) return;
    lastOptions = options;
    const selected = select.value;
    const latest = element("option", tasks.length ? "最新发布 · " + tasks[0].title : "最新发布");
    latest.value = "";
    const archive = tasks.slice(1).map(task => {
      const option = element("option", task.title);
      option.value = task.id;
      return option;
    });
    select.replaceChildren(latest, ...archive);
    select.value = archive.some(option => option.value === selected) ? selected : "";
    container.hidden = archive.length === 0;
  };
}

function taskQuery(taskId) {
  return taskId ? "?taskId=" + encodeURIComponent(taskId) : "";
}

function initializeTeacher() {
  const guide = byId("teacher-guide");
  byId("open-teacher-guide").addEventListener("click", () => guide.showModal());
  const storageKey = "classlab.teacher";
  const roomsKey = storageKey + ".classrooms";
  const roomPicker = byId("teacher-room-picker");
  const roomNavigation = byId("teacher-room-navigation");
  let credentials = JSON.parse(localStorage.getItem(storageKey) || "null");
  function readRoomRecords() {
    try {
      const saved = JSON.parse(localStorage.getItem(roomsKey) || "{}");
      return saved && typeof saved === "object" && !Array.isArray(saved) ? saved : {};
    } catch {
      return {};
    }
  }

  let roomRecords = readRoomRecords();

  function rememberRoom(name = "课堂 " + credentials.id.slice(0, 8)) {
    if (roomRecords[credentials.id]?.name === name &&
        roomRecords[credentials.id]?.teacherKey === credentials.teacherKey) return;
    roomRecords = readRoomRecords();
    roomRecords[credentials.id] = {...credentials, name};
    localStorage.setItem(roomsKey, JSON.stringify(roomRecords));
    renderRoomNavigation();
  }

  function renderRoomNavigation() {
    const placeholder = element("option", "选择课堂");
    placeholder.value = "";
    const rooms = Object.values(roomRecords).map(room => {
      const option = element("option", room.name);
      option.value = room.id;
      return option;
    });
    roomPicker.replaceChildren(placeholder, ...rooms);
    roomPicker.value = credentials?.id || "";
    roomNavigation.hidden = rooms.length <= Number(Boolean(credentials)) ||
      !byId("classroom-view").hidden || byId("dashboard").hasAttribute("data-preparing");
  }

  const headers = () => ({ "X-Teacher-Key": credentials.teacherKey });
  const endpoint = (suffix) => "/rooms/" + credentials.id + suffix;
  const renderSchedule = scheduleView(async slot => {
    await api(endpoint("/schedule/" + slot.id), { method: "DELETE", headers: headers() });
    feedback("已移除「" + slot.name + "」。", false, "schedule-feedback");
    await refresh();
  });
  const link = byId("join-link");
  const qrButton = byId("show-qr");
  const qrDialog = byId("qr-dialog");
  const caseRows = byId("case-editor-rows");
  const addCase = byId("add-case");
  const submissionDialog = byId("submission-dialog");
  const selectedTask = byId("teacher-task-picker");
  const renderTasks = taskPicker(selectedTask, byId("teacher-task-navigation"));
  let analysisSignature;
  let configurationTask;
  let publishedCases = [];
  const management = byId("management-view");
  const classroom = byId("classroom-view");
  const toggle = byId("toggle-classroom");
  let lastExerciseDraft = null;
  const notebook = initializeNotebookImport(byId("publish"), lesson => {
    const previous = draftValues();
    const occupied = ["title", "description", "starterCode"].some(key => previous[key]?.trim()) || previous.testCases.length || previous.pitfalls.length;
    if (occupied && JSON.stringify(previous) !== lastExerciseDraft && !confirm("载入互动练习将替换当前题目、代码、测试用例及易错点。请先保存需要的草稿。确定载入？")) return false;
    restoreCompose(lesson);
    detachDraft();
    lastExerciseDraft = JSON.stringify(draftValues());
    return true;
  });

  const form = byId("publish");
  const composer = byId("teacher-composer");
  const pitfallRows = byId("pitfall-rows");
  const addPitfall = byId("add-pitfall");
  const publishTask = byId("publish-task");
  const starter = form.elements.starterCode;
  const allowBlank = byId("allow-empty-starter");

  function syncStarter() {
    const hasCode = Boolean(starter.value.trim());
    byId("empty-starter-choice").hidden = hasCode;
    if (hasCode) allowBlank.checked = false;
    byId("starter-code-status").textContent = hasCode
      ? "此编辑框中的完整代码会发送给学生。"
      : "起始代码为空。可填入 Notebook 代码、粘贴代码，或选择让学生从空白开始。";
  }

  starter.addEventListener("input", syncStarter);
  syncStarter();

  form.addEventListener("invalid", event => {
    const firstInvalid = Array.from(form.elements).find(field => field.willValidate && !field.validity.valid);
    if (event.target !== firstInvalid) return;
    const row = firstInvalid.closest(".case-row");
    const label = firstInvalid.closest("label")?.textContent.trim() || "此字段";
    const message = row
      ? (row.parentElement === caseRows ? "测试用例" : "预期易错点") + " " +
        (Array.from(row.parentElement.children).indexOf(row) + 1) + " · " + label
      : label;
    const section = firstInvalid.closest("details");
    if (section) section.open = true;
    feedback(message + "：" + firstInvalid.validationMessage, true, "publish-feedback");
    firstInvalid.focus();
  }, true);

  const updatePreparationCounts = () => {
    byId("preparation-counts").textContent = caseRows.childElementCount + " 个用例 · " + pitfallRows.childElementCount + " 个易错点";
  };
  const countObserver = new MutationObserver(updatePreparationCounts);
  countObserver.observe(caseRows, {childList: true});
  countObserver.observe(pitfallRows, {childList: true});
  updatePreparationCounts();

  function prepare(enabled) {
    byId("dashboard").toggleAttribute("data-preparing", enabled);
    byId("dashboard").hidden = !enabled;
    byId("setup").hidden = enabled;
    byId("exit-preparation").hidden = !enabled;
    publishTask.disabled = enabled;
    renderRoomNavigation();
    if (enabled) {
      selectComposeMode("prep");
      byId("room-name").textContent = "课前备课";
      byId("notebook-file").focus();
    } else {
      byId("open-preparation").focus();
    }
  }

  byId("open-preparation").addEventListener("click", () => prepare(true));
  byId("exit-preparation").addEventListener("click", () => prepare(false));

  byId("new-classroom").addEventListener("click", () => {
    if (composer.inert) return;
    selectRoom(null);
    byId("create").reset();
    byId("create").elements.name.focus();
  });

  function rowData(rows) {
    return Array.from(rows.children, row => Object.fromEntries(
      Array.from(row.querySelectorAll("[data-field]"), field => [field.dataset.field, field.value])
    ));
  }

  function appendPitfall(values = {}, focus = true) {
    if (pitfallRows.childElementCount >= 8) return;
    const row = byId("pitfall-template").content.firstElementChild.cloneNode(true);
    for (const field of row.querySelectorAll("[data-field]")) field.value = values[field.dataset.field] ?? "";
    row.querySelector(".remove-pitfall").addEventListener("click", () => {
      row.remove();
      addPitfall.disabled = false;
      addPitfall.focus();
    });
    pitfallRows.append(row);
    addPitfall.disabled = pitfallRows.childElementCount >= 8;
    if (focus) row.querySelector("input").focus();
  }

  addPitfall.addEventListener("click", () => appendPitfall());
  function draftValues() {
    return { ...Object.fromEntries(new FormData(form)), testCases: rowData(caseRows), pitfalls: rowData(pitfallRows) };
  }

  const detachDraft = initializeLessonLibrary(draftValues, lesson => {
    restoreCompose(lesson);
    notebook.resetSelection();
    lastExerciseDraft = null;
  });

  // Keep quick paste and lesson preparation drafts independent while switching tabs.
  // This only affects the teacher form; the existing local lesson library is unchanged.
  let composeMode = "prep";
  let composeBuffers = {quick: null, prep: null};
  const roomDrafts = new Map();

  function restoreCompose(values = null) {
    for (const name of ["title", "description", "starterCode"]) {
      form.elements[name].value = values?.[name] || "";
    }
    caseRows.replaceChildren();
    pitfallRows.replaceChildren();
    addCase.disabled = addPitfall.disabled = false;
    for (const test of values?.testCases || []) appendCase(test, false);
    for (const pitfall of values?.pitfalls || []) appendPitfall(pitfall, false);
    allowBlank.checked = false;
    syncStarter();
  }

  function selectComposeMode(next) {
    if (next !== "quick" && next !== "prep") return;
    if (next !== composeMode) {
      composeBuffers[composeMode] = draftValues();
      composeMode = next;
      restoreCompose(composeBuffers[next]);
    }
    const preparing = next === "prep";
    byId("compose-quick").setAttribute("aria-pressed", String(!preparing));
    byId("compose-prep").setAttribute("aria-pressed", String(preparing));
    byId("compose-quick").classList.toggle("secondary", preparing);
    byId("compose-prep").classList.toggle("secondary", !preparing);
    byId("prep-library").hidden = !preparing;
    byId("notebook-import").hidden = !preparing;
    byId("teacher-optional-settings").open = false;
    byId("prep-library").open = false;
    byId("compose-hint").textContent = preparing
      ? "浏览 Notebook，将所需单元填入起始代码，再核对并发布。"
      : "填写标题并粘贴 C++ 代码，或选择让学生从空白开始。";
  }

  byId("compose-quick").addEventListener("click", () => selectComposeMode("quick"));
  byId("compose-prep").addEventListener("click", () => selectComposeMode("prep"));
  selectComposeMode("prep");

  function project(enabled) {
    if (qrDialog.open) qrDialog.close();
    if (submissionDialog.open) submissionDialog.close();
    management.hidden = enabled;
    classroom.hidden = !enabled;
    toggle.setAttribute("aria-pressed", String(enabled));
    toggle.textContent = enabled ? "返回管理" : "课堂投影";
    renderRoomNavigation();
  }

  toggle.addEventListener("click", () => {
    if (classroom.hidden && selectedTask.value) {
      selectedTask.value = "";
      void refresh();
    }
    project(classroom.hidden);
  });

  function appendCase(values = {}, focus = true) {
    if (caseRows.childElementCount >= 12) return;
    const row = byId("case-template").content.firstElementChild.cloneNode(true);
    row.querySelector(".remove-case").addEventListener("click", () => {
      row.remove();
      addCase.disabled = false;
      addCase.focus();
    });
    caseRows.append(row);
    for (const field of row.querySelectorAll("[data-field]")) {
      if (Object.hasOwn(values, field.dataset.field)) field.value = values[field.dataset.field];
    }
    addCase.disabled = caseRows.childElementCount >= 12;
    if (focus) row.querySelector("input").focus();
  }
  addCase.addEventListener("click", () => appendCase());


  async function praiseStudent(name, number) {
    try {
      await api(endpoint("/students/" + number + "/praise"), { method: "POST", headers: headers() });
      feedback("已嘉奖 " + name + "，其学生页面会收到提醒。");
    } catch (error) {
      feedback(error.message, true);
    }
  }

  async function removeStudent(student) {
    if (!confirm("将 " + student.name + " 移出课堂？其提交记录会一并删除且不可恢复。")) return;
    try {
      await api(endpoint("/students/" + student.number), { method: "DELETE", headers: headers() });
      await refresh();
    } catch (error) {
      feedback(error.message, true);
    }
  }

  function detailButton(number, taskId) {
    const button = element("button", "查看提交");
    button.type = "button";
    button.className = "secondary";
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        const roomId = credentials.id;
        const latest = await api(endpoint("/latest/" + number + "?taskId=" + encodeURIComponent(taskId)),
          { headers: headers() });
        if (credentials?.id !== roomId || management.hidden || configurationTask !== taskId) return;
        byId("submission-title").textContent = latest.name + "的最新提交";
        renderDiff(latest.starterCode, latest.code);
        displayResult(byId("teacher-result"), latest.result, publishedCases);
        const evidence = latest.pitfallEvidence || [];
        byId("submission-pitfalls").hidden = !evidence.length;
        byId("submission-pitfall-list").replaceChildren(...evidence.map(item => {
          const row = element("li");
          row.append(element("strong", item.name));
          if (item.note) row.append(element("p", item.note));
          if (item.needle) row.append(element("p", item.sourceMatch ? "发现源码线索。" : "未发现预设源码片段。"));
          if (item.testNumber) row.append(element("p", "用例 " + item.testNumber + " · " +
            (statusText[item.testStatus] || "无评测结果")));
          return row;
        }));
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
    const pitfalls = state.pitfallStats || [];
    byId("pitfall-analysis").hidden = !pitfalls.length;
    byId("pitfall-results").replaceChildren(...pitfalls.map(item => {
      const row = element("li");
      row.append(element("strong", item.name));
      if (item.note) row.append(element("p", item.note));
      if (item.needle) row.append(element("p", "源码片段命中 " + item.sourceMatches + " 人"), element("code", item.needle));
      if (item.testNumber) row.append(element("p", "用例 " + item.testNumber + " · " +
        item.testFailures + " 人失败 / " + item.testObserved + " 人有结果"));
      return row;
    }));
    if (configurationTask !== state.task?.id) {
      configurationTask = state.task?.id;
      publishedCases = state.task?.testCases || [];
      if (submissionDialog.open) submissionDialog.close();
      byId("teacher-case-config").replaceChildren(...publishedCases.map((test) => sampleBlock({
        ...test, name: test.name + (test.visibility === "hidden" ? "（隐藏）" : "（公开）"),
      })));
    }
    const stats = state.caseStats.map((test) => {
      const evaluated = test.passed + test.failed;
      const rate = evaluated ? "通过率 " + Math.round(100 * test.passed / evaluated) + "%" : "暂无用例结果";
      const title = test.name + (test.visibility === "hidden" ? "（隐藏）" : "（公开）");
      const causes = Object.entries(test.failureKinds).map(([key, count]) => statusText[key] + " " + count + " 人");
      return element("li", title + " · " + test.passed + " 通过 / " + test.failed + " 失败 · " + rate +
        (causes.length ? "（" + causes.join("，") + "）" : ""));
    });
    byId("case-stats").replaceChildren(...stats);
    byId("no-errors").hidden = state.errorGroups.length > 0;
    const groups = state.errorGroups.map((group) => {
      const item = element("li");
      item.append(element("strong", (categoryText[group.category] || "其他编译诊断") + " · " + group.count + " 人"));
      if (group.example) item.append(element("pre", group.example));
      for (const message of group.repeatedMessages || []) {
        item.append(element("p", "相同诊断片段 · " + message.count + " 人"),
          element("code", message.text));
      }
      item.append(detailButton(group.studentNumber, state.task.id));
      return item;
    });
    byId("error-groups").replaceChildren(...groups);
    byId("no-patterns").hidden = state.editPatterns.length > 0;
    byId("edit-patterns").replaceChildren(...state.editPatterns.map(group => {
      const item = element("li");
      const result = Object.entries(group.outcomes).map(([key, count]) =>
        (statusText[key] || key) + " " + count + " 人").join("，");
      item.append(element("strong", "原第 " + group.line + " 行位置 · " + group.count + " 人"),
        element("pre", [...group.before.map(s => "− " + s), ...group.after.map(s => "+ " + s)].join("\n")),
        element("p", result), detailButton(group.studentNumber, state.task.id));
      return item;
    }));
  }

  function selectRoom(next, keepComposer = false) {
    if (!keepComposer) {
      composeBuffers[composeMode] = draftValues();
      roomDrafts.set(credentials?.id || "", {mode: composeMode, buffers: composeBuffers});
      const draft = roomDrafts.get(next?.id || "");
      composeMode = draft?.mode || "prep";
      composeBuffers = draft?.buffers || {quick: null, prep: null};
      restoreCompose(composeBuffers[composeMode]);
      selectComposeMode(composeMode);
      notebook.resetSelection();
      detachDraft();
      lastExerciseDraft = null;
    } else {
      roomDrafts.delete("");
    }
    credentials = next;
    if (next) localStorage.setItem(storageKey, JSON.stringify(next));
    else localStorage.removeItem(storageKey);
    selectedTask.value = "";
    renderTasks();
    configurationTask = null;
    publishedCases = [];
    analysisSignature = undefined;
    byId("classroom-progress").hidden = true;
    byId("class-schedule").hidden = true;
    toggle.disabled = true;
    feedback("", false, "publish-feedback");
    feedback("");
    if (next) {
      byId("room-name").textContent = next.name || "课堂";
      showDashboard();
    } else {
      prepare(false);
    }
    project(false);
  }

  function showDashboard() {
    byId("dashboard").removeAttribute("data-preparing");
    byId("exit-preparation").hidden = true;
    publishTask.disabled = false;
    link.value = new URL("/join/" + credentials.id, location.origin).href;
    byId("setup").hidden = true;
    byId("dashboard").hidden = false;
    byId("projection-link").href = link.value;
    try {
      const qr = joinQr(link.value);
      qrButton.replaceChildren(qr);
      byId("qr-large").replaceChildren(qr.cloneNode(true));
      byId("projection-qr").replaceChildren(qr.cloneNode(true));
      byId("share-hint").textContent = "扫描二维码或打开链接即可进入学生页面。点击二维码可放大投影。";
      qrButton.hidden = false;
    } catch {
      qrButton.hidden = true;
      byId("projection-qr").replaceChildren();
      byId("share-hint").textContent = "二维码暂不可用，请复制加入链接。";
    }
  }

  function refreshStatus(message) {
    const status = byId("refresh-state");
    if (status.textContent !== message) status.textContent = message;
  }

  function showProgress(state) {
    rememberRoom(state.name);
    byId("classroom-progress").hidden = false;
    byId("class-schedule").hidden = false;
    toggle.disabled = false;
    renderSchedule(state.schedule);
    const archived = Boolean(selectedTask.value);
    renderTasks(state.tasks);
    if (!archived) {
      byId("projection-task").textContent = state.task?.title || "尚未发布任务";
      for (const metric of ["joined", "submitted", "accepted"]) {
        byId("projection-" + metric).textContent = state[metric];
      }
      const rate = state.joined ? Math.round(100 * state.submitted / state.joined) : 0;
      byId("projection-meter").value = rate;
      byId("projection-rate").textContent = state.joined ?
        state.submitted + " / " + state.joined + " 人已提交（" + rate + "%）" : "等待学生加入";
    }
    byId("projection-connection").textContent = "";
    byId("room-name").textContent = state.name;
    byId("current-task").textContent = state.task ?
      (archived ? "往期任务 · " : "当前任务 · ") + state.task.title : "尚未发布任务";
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
    const signature = JSON.stringify([archived, state.task?.id, state.students, state.caseStats, state.errorGroups, state.editPatterns, state.pitfallStats]);
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
      const actions = row.insertCell();
      if (archived) return row;
      const praise = element("button", "嘉奖");
      praise.type = "button";
      praise.className = "secondary";
      praise.addEventListener("click", () => praiseStudent(student.name, student.number));
      const remove = element("button", "移出");
      remove.type = "button";
      remove.className = "secondary";
      remove.addEventListener("click", () => removeStudent(student));
      actions.append(praise, remove);
      return row;
    });
    if (!rows.length) {
      const empty = document.createElement("tr");
      empty.classList.add("empty-row");
      const cell = empty.insertCell();
      cell.colSpan = 5;
      cell.textContent = "当前暂时无学生加入";
      rows.push(empty);
    }
    byId("students").replaceChildren(...rows);
  }

  const refresh = poll(async () => {
    if (!credentials) return;
    const room = credentials.id;
    const taskId = selectedTask.value;
    try {
      const state = await api(endpoint("/progress") + taskQuery(taskId), { headers: headers() });
      if (credentials?.id === room && selectedTask.value === taskId) showProgress(state);
    } catch (error) {
      if (credentials?.id === room && selectedTask.value === taskId) throw error;
    }
  }, (error) => {
    if (error.status === 403 || error.status === 404) {
      roomRecords = readRoomRecords();
      delete roomRecords[credentials.id];
      localStorage.setItem(roomsKey, JSON.stringify(roomRecords));
      selectRoom(null);
      feedback(error.message, true);
    } else {
      refreshStatus("连接中断，数值可能过时");
      byId("projection-connection").textContent = "连接中断，数值可能过时";
    }
  });

  const exportButton = byId("export-current-csv");
  exportButton.addEventListener("click", async () => {
    if (!credentials || exportButton.disabled) return;
    const roomId = credentials.id;
    const taskId = selectedTask.value;
    exportButton.disabled = true;
    exportButton.textContent = "正在导出…";
    feedback("", false, "export-feedback");
    try {
      const state = await api("/rooms/" + roomId + "/progress" + taskQuery(taskId), {
        headers: { "X-Teacher-Key": credentials.teacherKey }
      });
      if (credentials?.id !== roomId || selectedTask.value !== taskId) {
        feedback("课堂或任务已切换，请重新导出。", true, "export-feedback");
        return;
      }
      if (!state.task) {
        feedback("请先发布任务，再导出当前任务结果。", true, "export-feedback");
        return;
      }
      if (!Array.isArray(state.students) || state.students.length === 0) {
        feedback("当前课堂还没有学生，暂无可导出的结果。", true, "export-feedback");
        return;
      }
      const csv = buildClassroomCsv(state);
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "ClassLab-" + safeFilePart(state.task.title) + "-results.csv";
      document.body.append(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      feedback("已导出 " + state.students.length + " 名学生的当前任务结果。", false, "export-feedback");
    } catch (error) {
      feedback("导出失败：" + error.message, true, "export-feedback");
    } finally {
      exportButton.disabled = false;
      exportButton.textContent = "导出当前任务 CSV";
    }
  });

  selectedTask.addEventListener("change", () => {
    if (submissionDialog.open) submissionDialog.close();
    void refresh();
  });

  addEventListener("storage", event => {
    if (event.key !== roomsKey) return;
    roomRecords = readRoomRecords();
    renderRoomNavigation();
  });

  roomPicker.addEventListener("change", () => {
    const next = roomRecords[roomPicker.value];
    if (!next || next.id === credentials?.id || composer.inert ||
        byId("create").querySelector("button").disabled) {
      roomPicker.value = credentials?.id || "";
      return;
    }
    selectRoom(next);
    void refresh();
  });

  onSubmit("create", async (data) => {
    const room = await api("/rooms", { data });
    selectRoom({...room, name: data.name}, true);
    rememberRoom(data.name);
    await refresh();
  });

  onSubmit("add-slot", async data => {
    await api(endpoint("/schedule"), { headers: headers(), data: { ...data, day: Number(data.day) } });
    byId("add-slot").reset();
    feedback("已添加「" + data.name + "」。", false, "schedule-feedback");
    await refresh();
  }, "schedule-feedback");

  onSubmit("publish", async (data) => {
    if (!credentials) return;
    if (composeMode === "prep" && notebook.hasPendingSelection()) {
      throw new Error("所选组合尚未填入起始代码。请先填入，或从组合移除所选单元。");
    }
    if (!data.starterCode.trim() && !allowBlank.checked) {
      throw new Error("请填入起始代码，或勾选「让学生从空白开始」。");
    }
    if (!data.starterCode.trim()) data.starterCode = "";
    const cases = rowData(caseRows);
    const pitfalls = rowData(pitfallRows);
    if (cases.length) data.testCases = cases;
    if (pitfalls.length) data.pitfalls = pitfalls;
    composer.inert = true;
    try {
      await api(endpoint("/tasks"), { data, headers: headers() });
      selectedTask.value = "";
      // Clear only the published task. Keep the Notebook and the other workspace.
      composeBuffers[composeMode] = null;
      restoreCompose();
      if (composeMode === "prep") {
        notebook.finishTask();
        detachDraft();
        lastExerciseDraft = null;
      }
    } finally {
      composer.inert = false;
    }
    feedback("任务已发布：「" + data.title + "」。学生端将自动更新。", false, "publish-feedback");
    await refresh();
  }, "publish-feedback");

  byId("copy-link").addEventListener("click", () => copyText(link, "copy-feedback", "加入链接已复制。"));
  qrButton.addEventListener("click", () => qrDialog.showModal());

  if (credentials) {
    rememberRoom(roomRecords[credentials.id]?.name || credentials.name);
    showDashboard();
    void refresh();
  }
  renderRoomNavigation();
}

function renderHistory(history) {
  byId("submission-history").hidden = history.length === 0;
  const rows = history.map(item => {
    const time = new Date(item.receivedAt * 1000).toLocaleString();
    const score = item.total === undefined ? "" : " (" + item.passed + "/" + item.total + ")";
    return element("li", time + " · " + (statusText[item.status] || "状态未知") + score);
  });
  byId("history-list").replaceChildren(...rows);
}

function studentClassroomHistory(currentRoom) {
  const prefix = "classlab.student.";
  const namesKey = prefix + "classrooms";

  function names() {
    try {
      const value = JSON.parse(localStorage.getItem(namesKey) || "{}");
      return value && typeof value === "object" ? value : {};
    } catch {
      return {};
    }
  }

  function render() {
    const saved = names();
    const rooms = Object.keys(localStorage)
      .map(key => key.match(/^classlab\.student\.([a-f0-9]{32})$/)?.[1])
      .filter(Boolean);
    byId("student-classrooms").hidden = !rooms.some(id => id !== currentRoom);
    const rows = rooms.map(id => {
      const title = typeof saved[id] === "string" ? saved[id] : "课堂 " + id.slice(0, 8);
      const row = element("li");
      if (id === currentRoom) {
        row.textContent = title + "（当前课堂）";
      } else {
        const link = element("a", title);
        link.href = "/join/" + id;
        row.append(link);
      }
      return row;
    });
    byId("student-classroom-list").replaceChildren(...rows);
  }

  addEventListener("storage", event => {
    if (!event.key || event.key.startsWith(prefix)) render();
  });
  render();
  return {
    remember(name) {
      const saved = names();
      if (saved[currentRoom] !== name) {
        try {
          localStorage.setItem(namesKey, JSON.stringify({...saved, [currentRoom]: name}));
        } catch {}
      }
      render();
    },
    render,
  };
}

function initializeStudent() {
  const room = location.pathname.split("/").pop();
  const storageKey = "classlab.student." + room;
  const classrooms = studentClassroomHistory(room);
  const selectedTask = byId("student-task-picker");
  const renderTasks = taskPicker(selectedTask, byId("student-task-navigation"));
  let key = localStorage.getItem(storageKey);
  let currentTask = null;
  let resultSignature;
  let pendingSubmission;
  let running = false;
  const editor = byId("submit").elements.code;
  let praiseSeqSeen = Number(localStorage.getItem(storageKey + ".praiseSeq") || 0);
  let praiseTimer;
  const endpoint = (suffix) => "/rooms/" + room + suffix;
  const headers = () => ({ "X-Student-Key": key });
  const draftKey = (id) => storageKey + ".draft." + id;
  const renderSchedule = scheduleView();

  function appendRunResultCopy(panel, result) {
    const button = element("button", "复制结果");
    button.type = "button";
    button.className = "secondary";
    button.id = "copy-run-result";

    const status = element("p");
    status.id = "run-copy-feedback";
    status.className = "inline-status";
    status.setAttribute("role", "status");

    const fallback = element("textarea");
    fallback.id = "run-copy-fallback";
    fallback.hidden = true;
    fallback.readOnly = true;
    fallback.rows = 5;
    fallback.setAttribute("aria-label", "待手动复制的运行结果");

    button.addEventListener("click", async () => {
      fallback.value = runResultCopyText(result);
      fallback.hidden = false;
      const copied = await copyText(fallback, "run-copy-feedback", "运行结果已复制。");
      if (copied) fallback.hidden = true;
    });
    const actions = element("div");
    actions.className = "run-result-actions";
    actions.append(button, status, fallback);
    panel.append(actions);
  }

  function showTask(state) {
    executionAvailable = Boolean(state.executionAvailable);
    interactive = Boolean(state.interactiveAvailable);
    renderSchedule(state.schedule);
    byId("setup").hidden = true;
    byId("workspace").hidden = false;
    byId("connection").textContent = "";
    feedback("");
    byId("room-name").textContent = state.roomName;
    if (byId("student-name").textContent !== state.studentName) {
      classrooms.remember(state.roomName);
    }
    byId("student-name").textContent = state.studentName;
    const praiseSeq = Number(state.praiseSeq || 0);
    if (praiseSeq > praiseSeqSeen) {
      praiseSeqSeen = praiseSeq;
      localStorage.setItem(storageKey + ".praiseSeq", String(praiseSeq));
      const toast = byId("praise-toast");
      toast.classList.remove("show");
      void toast.offsetWidth;
      toast.classList.add("show");
      clearTimeout(praiseTimer);
      praiseTimer = setTimeout(() => toast.classList.remove("show"), 4000);
    }
    byId("waiting").hidden = Boolean(state.task);
    byId("assignment").hidden = !state.task;
    const archived = Boolean(selectedTask.value);
    renderTasks(state.tasks);
    byId("archive-notice").hidden = !archived;
    editor.readOnly = archived;
    for (const id of ["reset-code", "submit-code", "submit-shortcut", "run-controls", "run-state",
      "open-optcpp"]) {
      byId(id).hidden = archived;
    }
    if (archived && live) forgetLive();
    syncRunControls();
    const signature = JSON.stringify([state.task?.id, state.latestResult, state.submissionHistory]);
    if (signature !== resultSignature) {
      resultSignature = signature;
      byId("latest-result").hidden = !state.latestResult;
      displayResult(byId("student-result"), state.latestResult);
      renderHistory(state.submissionHistory || []);
    }
    if (!state.task || state.task.id === currentTask?.id) return;
    feedback("", false, "submit-feedback");
    byId("run-result").hidden = true;
    byId("run-result").replaceChildren();
    forgetLive();
    byId("optcpp-fallback").hidden = true;
    byId("optcpp-status").textContent = "";
    byId("editor-feedback").textContent = currentTask && !archived ? "已打开最新任务。" : "";
    currentTask = state.task;
    syncRunControls();
    byId("task-title").textContent = currentTask.title;
    const taskDescription = currentTask.description || "";
    byId("task-description").textContent = taskDescription;
    byId("task-description").hidden = !taskDescription.trim();
    const tests = currentTask.testCases || [];
    byId("public-tests").hidden = !tests.length;
    byId("public-tests").open = false;
    byId("student-public-tests").replaceChildren(...tests.map(sampleBlock));
    editor.value = localStorage.getItem(draftKey(currentTask.id)) ?? currentTask.starterCode;
  }

  const refresh = poll(async () => {
    if (!key) return;
    const taskId = selectedTask.value;
    const state = await api(endpoint("/task") + taskQuery(taskId), { headers: headers() });
    if (selectedTask.value === taskId) showTask(state);
  }, (error) => {
    if (error.status === 403 || error.status === 404) {
      forgetLive();
      localStorage.removeItem(storageKey);
      key = null;
      currentTask = null;
      selectedTask.value = "";
      renderTasks();
      classrooms.render();
      byId("setup").hidden = false;
      byId("workspace").hidden = true;
      feedback(error.message, true);
    } else {
      const target = byId("workspace").hidden ? "feedback" : "connection";
      feedback("任务刷新失败，系统正在重试。", true, target);
    }
  });

  selectedTask.addEventListener("change", () => { forgetLive(); void refresh(); });

  onSubmit("join", async (data) => {
    const result = await api(endpoint("/students"), { data });
    key = result.studentKey;
    praiseSeqSeen = 0;
    localStorage.removeItem(storageKey + ".praiseSeq");
    localStorage.setItem(storageKey, key);
    classrooms.render();
    await refresh();
  });

  byId("copy-code").addEventListener("click", () => copyText(editor, "editor-feedback", "代码已复制。"));

  const input = byId("submit").elements.runInput;
  const activeStatuses = new Set(["compiling", "running", "stopping"]);
  let live = null;
  let interactive = false;
  let executionAvailable = false;
  let livePolling = false;
  let liveAction = false;

  function syncRunControls() {
    const archived = Boolean(selectedTask.value);
    const active = Boolean(live);
    const enabled = !archived && executionAvailable && Boolean(currentTask);
    byId("run-controls").disabled = !enabled || running || active;
    editor.readOnly = archived || running || active;
    byId("reset-code").disabled = running || active;
    byId("stdin-panel").hidden = archived || (!enabled && !active) || (interactive && !active);
    byId("live-actions").hidden = !active;
    input.disabled = archived || running || (active && (!live?.stdinOpen || liveAction));
    byId("send-stdin").disabled = !live?.stdinOpen || liveAction;
    byId("send-eof").disabled = !live?.stdinOpen || liveAction;
    byId("stop-run").disabled = !live || liveAction || live.status === "stopping";
    byId("stdin-label").textContent = interactive || active ? "交互标准输入（stdin）" : "完整标准输入（批处理）";
    byId("stdin-hint").textContent = interactive || active
      ? "输入一行或多行后点击发送。程序在同一进程中继续执行；点击 EOF 才主动结束输入流。"
      : "运行前请一次填入程序所需的全部输入。运行时会关闭 stdin；这不是交互终端。无输入程序可留空。";
    byId("run-state").textContent = active ? (live.status === "compiling" ? "正在编译…" : live.status === "stopping" ? "正在停止…" :
      "程序仍在运行，可继续发送输入；不保证正在等待 stdin。") :
      !enabled ? "执行器不可用，或当前正在查看历史任务。" :
      running ? "正在编译和运行…" : interactive ? "Run 启动一个持续进程，不计入正式提交。" :
      "批处理运行：请先填写完整 stdin，再点击运行。不计入正式提交。";
  }

  function showRunResult(result, active = false) {
    const panel = byId("run-result");
    panel.replaceChildren();
    displayResult(panel, result);
    if (Object.hasOwn(result, "exitCode")) panel.append(element("p", "退出状态 " + result.exitCode));
    if (Object.hasOwn(result, "stdout")) panel.append(element("strong", "标准输出"), element("pre", result.stdout || (active ? "" : "（空）")));
    if (result.stderr) panel.append(element("strong", "标准错误"), element("pre", result.stderr));
    if (result.error) panel.append(element("p", result.error));
    panel.hidden = false;
    appendRunResultCopy(panel, result);
  }

  function sessionRequest(run, action, extra = {}) {
    return api(endpoint("/run-session"), {headers: headers(), timeoutMs: 7000,
      data: {action, taskId: run.taskId, ...(run.id ? {sessionId: run.id} : {}), ...extra}});
  }

  function forgetLive() {
    const previous = live;
    live = null;
    if (previous?.id && key) void sessionRequest(previous, "stop").catch(() => {});
    input.value = "";
    syncRunControls();
  }

  function acceptLive(run, result) {
    if (live !== run) {
      if (result.sessionId && key) void sessionRequest({...run, id: result.sessionId}, "stop").catch(() => {});
      return;
    }
    if (["input_closed", "input_limit"].includes(result.status)) {
      byId("run-action-feedback").textContent = result.error || result.status;
      return;
    }
    if (result.sessionId) run.id = result.sessionId;
    run.status = result.status;
    run.stdinOpen = Boolean(result.stdinOpen);
    const signature = JSON.stringify(result);
    if (signature !== run.signature) {
      run.signature = signature;
      showRunResult(result, activeStatuses.has(result.status));
    }
    if (!activeStatuses.has(result.status)) {
      live = null;
      input.value = "";
    }
    syncRunControls();
  }

  async function pollLive() {
    const run = live;
    if (!run?.id || livePolling || liveAction) return;
    livePolling = true;
    const revision = run.revision || 0;
    try {
      const result = await sessionRequest(run, "poll");
      if (live === run && !liveAction && revision === (run.revision || 0)) {
        if (result.status === "judge_error" && !result.sessionId)
          byId("run-action-feedback").textContent = "会话连接暂时不可用，正在重试。";
        else acceptLive(run, result);
      }
    } catch (error) {
      if (live === run) {
        if (error.status === 403 || error.status === 409) forgetLive();
        else byId("run-action-feedback").textContent = "会话连接暂时不可用，正在重试。";
      }
    } finally {
      livePolling = false;
    }
  }

  setInterval(pollLive, 350);
  addEventListener("pagehide", () => {
    if (!live?.id || !key) return;
    fetch("/api" + endpoint("/run-session"), {method: "POST", keepalive: true,
      headers: {...headers(), "Content-Type": "application/json"},
      body: JSON.stringify({action: "stop", taskId: live.taskId, sessionId: live.id})}).catch(() => {});
  });

  async function liveCommand(action) {
    const run = live;
    if (!run || liveAction || (action !== "stop" && !run.stdinOpen)) return;
    if (!run.id) {
      if (action === "stop") forgetLive();
      return;
    }
    const original = input.value;
    const extra = action === "input" ? {input: original.endsWith("\n") ? original : original + "\n"} : {};
    run.revision = (run.revision || 0) + 1;
    liveAction = true;
    syncRunControls();
    byId("run-action-feedback").textContent = "";
    try {
      const result = await sessionRequest(run, action, extra);
      if (live === run) {
        if (action === "input" && !["input_closed", "input_limit", "judge_error", "not_found"].includes(result.status)) input.value = "";
        if (result.status === "judge_error" && !result.sessionId)
          byId("run-action-feedback").textContent = "未确认操作结果；请检查会话状态。系统不会自动重发输入。";
        else acceptLive(run, result);
      }
    } catch (error) {
      if (live === run) byId("run-action-feedback").textContent = "操作未确认：" + error.message + "。请检查输出后再决定是否重试。";
    } finally {
      liveAction = false;
      syncRunControls();
    }
  }

  byId("send-stdin").addEventListener("click", () => void liveCommand("input"));
  byId("send-eof").addEventListener("click", () => void liveCommand("eof"));
  byId("stop-run").addEventListener("click", () => void liveCommand("stop"));
  const fallback = byId("optcpp-fallback");
  const optStatus = byId("optcpp-status");
  byId("open-optcpp").addEventListener("click", () => {
    fallback.hidden = true;
    optStatus.textContent = "";
    if (!editor.reportValidity()) return;

    // Keep the existing external display-mode handoff with no pre-seeded stdin.
    const state = new URLSearchParams({
      code: editor.value,
      curInstr: "0",
      mode: "display",
      py: "cpp",
      rawInputLstJSON: "[]"
    });
    const url = "https://dive4dec.github.io/OPT_CPP/visualize.html#" + state;
    if (url.length > 8192) {
      fallback.hidden = false;
      optStatus.textContent = "已显示手动复制方式。";
      return;
    }
    // Preserve the teammate's one-click external tab flow; never embed OPT CPP.
    window.open(url, "_blank", "noopener,noreferrer");
  });
  byId("copy-opt-code").addEventListener("click", () => copyText(editor, "optcpp-status", "当前代码已复制。"));

  byId("reset-code").addEventListener("click", () => {
    if (!currentTask) {
      feedback("目前没有可恢复的任务。", true, "editor-feedback");
      return;
    }
    if (!window.confirm("确定要放弃当前修改，并恢复教师提供的起始代码吗？")) return;
    editor.value = currentTask.starterCode || "";
    saveEditorDraft("已恢复起始代码，草稿也已更新。");
  });

  byId("download-code").addEventListener("click", () => {
    if (!currentTask) {
      feedback("目前没有可下载的代码。", true, "editor-feedback");
      return;
    }
    const safeName = (currentTask.title || "classlab-code")
      .trim()
      .replace(/[<>:"/\\|?*\x00-\x1F]/g, "-")
      .replace(/\s+/g, "-")
      .slice(0, 60) || "classlab-code";
    const file = new Blob([editor.value], { type: "text/x-c++src;charset=utf-8" });
    const url = URL.createObjectURL(file);
    const link = document.createElement("a");
    link.href = url;
    link.download = safeName + ".cpp";
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    byId("editor-feedback").textContent = "C++ 代码已下载。";
  });

  editor.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter" && !event.isComposing && !event.repeat) {
      event.preventDefault();
      editor.form.requestSubmit(editor.form.querySelector("button[type=submit]"));
    }
  });
  function saveEditorDraft(message) {
    if (!currentTask) return;
    try {
      localStorage.setItem(draftKey(currentTask.id), editor.value);
      byId("editor-feedback").textContent = message;
    } catch {
      byId("editor-feedback").textContent = "草稿无法保存，请在刷新前复制代码。";
    }
  }

  editor.addEventListener("input", () => {
    if (!live && !running) {
      byId("run-result").hidden = true;
      byId("run-result").replaceChildren();
    }
    saveEditorDraft("草稿已保存在此浏览器。");
  });

  byId("run-code").addEventListener("click", async () => {
    if (running || live || selectedTask.value || !currentTask || !editor.reportValidity()) return;
    const taskId = currentTask.id;
    const code = editor.value;
    const panel = byId("run-result");
    byId("run-action-feedback").textContent = "";
    panel.hidden = true;
    panel.replaceChildren();
    if (interactive) {
      const run = {taskId, code, id: null, status: "compiling", stdinOpen: false};
      live = run;
      input.value = "";
      syncRunControls();
      try {
        acceptLive(run, await sessionRequest(run, "start", {code}));
      } catch (error) {
        if (live === run) {
          live = null;
          showRunResult({status: "request_error", error: error.message});
          syncRunControls();
        }
      }
      return;
    }
    // Explicit batch fallback: provide all input before execution, no probe.
    const runInput = input.value;
    running = true;
    syncRunControls();
    try {
      const result = await api(endpoint("/run"), {headers: headers(), timeoutMs: 115000,
        data: {taskId, code, input: runInput, probe: false}});
      if (taskId !== currentTask?.id || selectedTask.value || code !== editor.value) return;
      showRunResult(result);
    } catch (error) {
      if (taskId === currentTask?.id && !selectedTask.value && code === editor.value)
        showRunResult({status: "request_error", error: error.message});
    } finally {
      running = false;
      syncRunControls();
      await refresh();
    }
  });

  onSubmit("submit", async ({ code }) => {
    if (selectedTask.value || !currentTask) return;
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
        const receivedAt = Number(receipt.receivedAt);
        const submittedAt = Number.isFinite(receivedAt) && receivedAt > 0
          ? new Date(receivedAt * 1000)
          : new Date();
        const submittedTime = submittedAt.toLocaleString(undefined, {
          dateStyle: "medium",
          timeStyle: "short"
        });
        feedback(message + " 提交时间：" + submittedTime, false, "submit-feedback");
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
