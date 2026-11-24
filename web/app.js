
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
    throw new RequestError("Connection lost. Please try again.", 0);
  } finally {
    clearTimeout(timeout);
  }
  if (!result) throw new RequestError("Could not read the server response. Check the preview connection.", 0);
  if (!response.ok) throw new RequestError(result.error || "Request failed.", response.status);
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
    byId(status).textContent = "Text selected. Use your browser's Copy command.";
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
  received: "Submitted",
  success: "Run successful",
  compiling: "Compiling",
  running: "Running",
  stopping: "Stopping",
  stopped: "Stopped",
  idle_timeout: "Input/output inactivity timeout",
  busy: "Execution slots occupied",
  not_found: "Execution session ended",
  request_error: "Request error",
  judge_unavailable: "Ungraded · Runner unavailable",
  judge_error: "Grading service error",
  pending: "Grading",
  queued: "Queued for grading",
  judge_queue_full: "Ungraded · Queue full",
  accepted: "All tests passed",
  passed: "Passed",
  wrong_answer: "Wrong answer",
  compilation_error: "Compilation error",
  runtime_error: "Runtime error",
  time_limit: "Time limit exceeded",
  resource_limit: "Resource limit exceeded",
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
    sections.push("DEMO REPLAY — Prerecorded result. The current C++ code was neither compiled nor run.");
  }
  if (result.status) {
    sections.push("Run status: " + (statusText[result.status] || result.status));
  }
  if (result.error) sections.push("Runtime error:\n" + String(result.error));
  if (result.diagnostic) sections.push("Compiler diagnostics:\n" + String(result.diagnostic));
  if (Object.hasOwn(result, "stdout")) {
    sections.push("Standard output:\n" + String(result.stdout ?? ""));
  }
  if (Object.hasOwn(result, "stderr")) {
    sections.push("Standard error:\n" + String(result.stderr ?? ""));
  }
  if (Object.hasOwn(result, "exitCode")) {
    sections.push("Exit status: " + String(result.exitCode));
  }
  return sections.length ? sections.join("\n\n") : "Run result: No output to copy.";
}

const categoryText = {
  missing_semicolon: "Possible missing semicolon",
  syntax: "Syntax error",
  undeclared_identifier: "Undeclared identifier",
  type_mismatch: "Type mismatch",
  header_or_namespace: "Header or namespace issue",
  other: "Other compiler diagnostics",
};

function element(tag, text) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  return node;
}

function scheduleView(onRemove) {
  const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
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
        const remove = element("button", "Remove");
        remove.type = "button";
        remove.className = "secondary";
        remove.setAttribute("aria-label", "Remove " + slot.name + " " + label);
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
  for (const [field, label] of [["input", "Standard input"], ["expectedOutput", "Expected output"], ["actualOutput", "Actual output"]]) {
    if (Object.hasOwn(test, field)) {
      block.append(element("p", label), element("pre", test[field] || "(empty)"));
    }
  }
  return block;
}

function displayResult(container, result, teacherCases) {
  container.replaceChildren();
  if (!result) return;
  const score = result.total === undefined ? "" : " · " + result.passed + "/" + result.total + " passed";
  container.append(element("p", (statusText[result.status] || "Unknown result") + score));
  if (result.demoFixture) container.append(element("p", "Prerecorded result. The current C++ code was neither compiled nor run."));
  if (result.diagnostic) container.append(element("pre", result.diagnostic));
  if (teacherCases) {
    for (const test of result.cases || []) {
      const config = teacherCases.find(item => item.id === test.testId);
      const name = config ? config.name + (config.visibility === "hidden" ? " (hidden)" : "") : "Test case " + test.testId;
      const details = element("details");
      details.append(element("summary", name + " · " + (statusText[test.status] || "Unknown result")),
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
    return (lines.find(line => !/^(?:%%|#\s*include\b|using\s+namespace\b)/.test(line)) || lines[0] || "(empty cell)").slice(0, 100);
  }

  function showSelection() {
    const numbers = cells.filter((_, position) => selected.has(position)).map(cell => cell.index + 1);
    selection.textContent = numbers.length
      ? "Selected cells: " + numbers.join(" → ") + (selectionApplied ? " added to starter code." : " pending. Apply this selection to the starter code.")
      : "No cells selected.";
    assemble.disabled = !numbers.length;
    combination.hidden = !numbers.length && (!cells[current] || toggleCell.hidden);
    combinationSummary.textContent = "Combine cells (advanced)" + (numbers.length
      ? " · " + numbers.length + (selectionApplied ? " applied" : " pending") : "");
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
      const label = cell.exercise ? "Interactive exercise" : cell.protected ? "Teacher preview only / loading disabled" : kindOf(cell) === "cpp" ? "C++" : kindOf(cell) === "markdown" ? "Markdown" : "Other code";
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
        meta.textContent += " · Selected";
      }
      button.addEventListener("click", () => {
        current = position;
        showCell();
        if (cell.exercise) importExercise(cell);
      });
      return button;
    });
    list.replaceChildren(...entries);
    if (!entries.length) list.append(element("p", "No matching cells. Change the search or filter."));
  }

  function showCell() {
    const cell = cells[current];
    if (!cell) return;
    currentLabel.textContent = "Cell " + (cell.index + 1) + " · " +
      (cell.exercise ? cell.exercise.title : cell.protected ? "Teacher only / invalid exercise metadata" : kindOf(cell) === "cpp" ? "C++ code" : kindOf(cell) === "markdown" ? "Markdown" : "Other code");
    preview.textContent = cell.code;
    const isCode = cell.kind === "code";
    use.hidden = !isCode || cell.protected;
    use.textContent = cell.exercise ? "Load interactive exercise" : "Use this cell as starter code";
    toggleCell.hidden = !isCode || cell.protected || Boolean(cell.exercise);
    appendText.hidden = isCode || cell.protected;
    toggleCell.textContent = selected.has(current) ? "Remove from selection" : "Add to selection";
    toggleCell.setAttribute("aria-pressed", String(selected.has(current)));
    status.textContent = cell.warning || (cell.exercise
      ? "Test cases: " + cell.exercise.testCases.length + ". Review before publishing."
      : isCode ? preparedSource(cell).error || "Preview only. Use this cell as starter code or add it to the selection."
        : "Preview only. You can append this cell to the task description.");
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
    if (!cell || cell.kind !== "code") return {error: "Only code cells can be used as C++ starter code."};
    if (cell.protected) return {error: cell.warning};
    if (cell.exercise) return {error: "Load interactive exercises individually to keep their code and test cases together."};
    let code = cell.code;
    const notes = [];
    const magic = code.match(/^\s*%%([\w-]+)[^\r\n]*(?:\r?\n|$)/);
    if (magic) {
      const name = magic[1].toLowerCase();
      if (name === "cpp" && !/^\s*%%cpp[ \t]*(?:\r?\n|$)/.test(code)) return {error: "Cell " + (cell.index + 1) + " only supports %%cpp without arguments. Edit the cell manually."};
      if (name !== "cpp") return {error: "Cell " + (cell.index + 1) +
        " uses %%" + name + ", which is not standard C++. Review and convert it manually."};
      code = code.slice(magic[0].length);
      notes.push("Cell " + (cell.index + 1) + ": Removed %%cpp. Check the resulting C++ code.");
    }
    if (/^\s*(?:from\s+\S+\s+import\s+|import\s+\w+|def\s+\w+\s*\()/m.test(code)) {
      return {error: "Cell " + (cell.index + 1) + " appears to contain Python. It cannot be inserted as C++ starter code."};
    }
    if (/(?:^|\n)\s*[%!](?![%=])/.test(code)) {
      return {error: "Cell " + (cell.index + 1) + " contains unsupported notebook directives. Convert them manually."};
    }
    if (!code.trim()) return {error: "Cell " + (cell.index + 1) + " has no C++ code to add."};
    return {code, notes};
  }

  function fillCode(code, source, notes) {
    if (code.length > 20000 || new TextEncoder().encode(code).length > 65536) {
      status.textContent = "The selected code exceeds the starter code length limit.";
      return false;
    }
    const mainCount = (code.match(/\bmain\s*\(/g) || []).length;
    if (mainCount === 0) notes.push("No main() found. If this is a fragment, add an entry point and any missing dependencies.");
    if (mainCount > 1) notes.push("Multiple main() functions found. Edit the code to keep one entry point.");
    form.elements.starterCode.value = code;
    form.elements.starterCode.dispatchEvent(new Event("input"));
    status.textContent = [source + " added to starter code.", ...notes].join(" ");
    return true;
  }

  picker.addEventListener("change", async () => {
    clear();
    const file = picker.files[0];
    if (!file) return;
    const readVersion = version;
    if (!file.name.toLowerCase().endsWith(".ipynb") || file.size > 2 * 1024 * 1024) {
      status.textContent = "Choose an .ipynb file no larger than 2 MiB.";
      return;
    }
    try {
      const notebook = JSON.parse(await file.text());
      if (readVersion !== version) return;
      const parsed = ClassLabNotebook.parse(notebook);
      cells = parsed.cells;
      overview.textContent = file.name + " · Total cells: " + parsed.total + " · Interactive exercises: " + parsed.count + (parsed.warnings ? " · Needs review: " + parsed.warnings : "");
      overview.hidden = false;
      if (parsed.count) {
        filter.value = "exercise";
        current = cells.findIndex(cell => cell.exercise);
      }
      if (!cells.length) {
        status.textContent = "This notebook contains no readable code or Markdown cells.";
        return;
      }
      fields.hidden = false;
      showCell();
      showSelection();
    } catch {
      if (readVersion === version) status.textContent = "Could not read the file. Choose a valid version 4 notebook.";
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
      currentLabel.textContent = "No matching cells";
      preview.textContent = "";
      use.hidden = toggleCell.hidden = appendText.hidden = true;
      showSelection();
      status.textContent = "No matching cells. Change the search or filter.";
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
      status.textContent = "Your edits were kept. Select Load interactive exercise to try again.";
      return;
    }
    resetSelection();
    status.textContent = "Exercise loaded. Review the instructions and cases before publishing." + (cell.warning ? " " + cell.warning : "");
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
    if (parts.length && fillCode(parts.join("\n\n"), "Selected cells", notes)) {
      selectionApplied = true;
      showSelection();
    }
  });
  appendText.addEventListener("click", () => {
    if (!cells[current] || cells[current].kind !== "markdown" || cells[current].protected) return;
    const field = form.elements.description;
    const next = [field.value, cells[current].code.trim()].filter(Boolean).join("\n\n");
    if (next.length > field.maxLength || new TextEncoder().encode(next).length > 10000) {
      status.textContent = "The combined description is too long. Copy the part you need from the preview.";
      return;
    }
    field.value = next;
    status.textContent = "Markdown appended as editable plain text.";
  });
  function resetSelection() {
    selected.clear();
    selectionApplied = false;
    if (cells.length) renderList();
    showSelection();
    toggleCell.textContent = "Add to selection";
    toggleCell.setAttribute("aria-pressed", "false");
  }

  return {
    hasPendingSelection: () => selected.size > 0 && !selectionApplied,
    resetSelection,
    finishTask() {
      if (!cells.length) return;
      resetSelection();
      combination.open = false;
      status.textContent = "Notebook retained. Browse the cells to prepare the next exercise.";
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
  byId("diff-summary").textContent = rows === null ? "The changes are too large for an inline diff. Compare the two full listings below." :
    panel.hidden ? "Identical to the starter code after normalizing line endings." :
    "Lines added: " + added + "; lines removed: " + removed + ". The left column shows original line numbers and the right column shows new line numbers.";
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
    feedback("Could not read the lesson drafts.", true, "draft-feedback");
    return [];
  }

  function render(id = "") {
    const options = drafts().map(draft => {
      const option = element("option", draft.lesson.title);
      option.value = draft.id;
      return option;
    });
    picker.replaceChildren(element("option", "Select an exercise"), ...options);
    picker.firstElementChild.value = "";
    picker.value = id;
    if (!picker.value) picker.value = "";
    open.disabled = remove.disabled = !picker.value;
    update.hidden = !loaded;
  }

  function save(id) {
    const lesson = serialize();
    if (!lesson.title.trim()) {
      feedback("Enter an exercise title before saving.", true, "draft-feedback");
      return;
    }
    const values = drafts();
    const existing = id && values.find(draft => draft.id === id);
    if (id && !existing) {
      feedback("This draft was deleted. Save it as a new exercise.", true, "draft-feedback");
      return;
    }
    if (!existing && values.some(draft => draft.lesson.title.trim().toLowerCase() === lesson.title.trim().toLowerCase())) {
      feedback("An exercise with this name already exists. Rename it before saving.", true, "draft-feedback");
      return;
    }
    if (!existing && values.length >= 25) {
      feedback("The exercise library holds up to 25 drafts.", true, "draft-feedback");
      return;
    }
    const record = existing || { id: String(Date.now()) + "-" + Math.random().toString(36).slice(2) };
    record.lesson = lesson;
    if (!existing) values.push(record);
    try {
      localStorage.setItem(key, JSON.stringify(values));
      loaded = record.id;
      render(loaded);
      feedback("Exercise saved in this browser.", false, "draft-feedback");
    } catch {
      feedback("Could not save to browser storage. You can still copy the editor contents.", true, "draft-feedback");
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
    feedback("Exercise loaded. You can edit or publish it.", false, "draft-feedback");
  });
  remove.addEventListener("click", () => {
    if (!confirm("Delete the selected draft from this browser?")) return;
    const id = picker.value;
    try {
      localStorage.setItem(key, JSON.stringify(drafts().filter(draft => draft.id !== id)));
      if (loaded === id) loaded = undefined;
      render();
      feedback("Draft deleted.", false, "draft-feedback");
    } catch {
      feedback("Could not delete the draft.", true, "draft-feedback");
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
    const latest = element("option", tasks.length ? "Latest task · " + tasks[0].title : "Latest task");
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

  function rememberRoom(name = "Classroom " + credentials.id.slice(0, 8)) {
    if (roomRecords[credentials.id]?.name === name &&
        roomRecords[credentials.id]?.teacherKey === credentials.teacherKey) return;
    roomRecords = readRoomRecords();
    roomRecords[credentials.id] = {...credentials, name};
    localStorage.setItem(roomsKey, JSON.stringify(roomRecords));
    renderRoomNavigation();
  }

  function renderRoomNavigation() {
    const placeholder = element("option", "Select a classroom");
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
    feedback("Removed “" + slot.name + "”.", false, "schedule-feedback");
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
    if (occupied && JSON.stringify(previous) !== lastExerciseDraft && !confirm("Loading this exercise replaces the current title, code, test cases, and pitfalls. Save any draft you want to keep. Load the exercise?")) return false;
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
      ? "Students will receive all the code in this editor."
      : "The starter code is empty. Add code from a notebook, paste code, or let students start with a blank editor.";
  }

  starter.addEventListener("input", syncStarter);
  syncStarter();

  form.addEventListener("invalid", event => {
    const firstInvalid = Array.from(form.elements).find(field => field.willValidate && !field.validity.valid);
    if (event.target !== firstInvalid) return;
    const row = firstInvalid.closest(".case-row");
    const label = firstInvalid.closest("label")?.textContent.trim() || "this field";
    const message = row
      ? (row.parentElement === caseRows ? "Test case" : "Expected pitfall") + " " +
        (Array.from(row.parentElement.children).indexOf(row) + 1) + " · " + label
      : label;
    const section = firstInvalid.closest("details");
    if (section) section.open = true;
    feedback(message + ": " + firstInvalid.validationMessage, true, "publish-feedback");
    firstInvalid.focus();
  }, true);

  const updatePreparationCounts = () => {
    byId("preparation-counts").textContent = "Test cases: " + caseRows.childElementCount + " · Pitfalls: " + pitfallRows.childElementCount;
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
      byId("room-name").textContent = "Lesson preparation";
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
      ? "Browse the notebook, add the cells you need to the starter code, then review and publish."
      : "Enter a title and paste C++ code, or let students start with a blank editor.";
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
    toggle.textContent = enabled ? "Back to dashboard" : "Classroom projection";
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
      feedback("Praise sent to " + name + ". A notification will appear on the student's page.");
    } catch (error) {
      feedback(error.message, true);
    }
  }

  async function removeStudent(student) {
    if (!confirm("Remove " + student.name + " from the classroom? Their submission history will be permanently deleted.")) return;
    try {
      await api(endpoint("/students/" + student.number), { method: "DELETE", headers: headers() });
      await refresh();
    } catch (error) {
      feedback(error.message, true);
    }
  }

  function detailButton(number, taskId) {
    const button = element("button", "View submission");
    button.type = "button";
    button.className = "secondary";
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        const roomId = credentials.id;
        const latest = await api(endpoint("/latest/" + number + "?taskId=" + encodeURIComponent(taskId)),
          { headers: headers() });
        if (credentials?.id !== roomId || management.hidden || configurationTask !== taskId) return;
        byId("submission-title").textContent = latest.name + "'s latest submission";
        renderDiff(latest.starterCode, latest.code);
        displayResult(byId("teacher-result"), latest.result, publishedCases);
        const evidence = latest.pitfallEvidence || [];
        byId("submission-pitfalls").hidden = !evidence.length;
        byId("submission-pitfall-list").replaceChildren(...evidence.map(item => {
          const row = element("li");
          row.append(element("strong", item.name));
          if (item.note) row.append(element("p", item.note));
          if (item.needle) row.append(element("p", item.sourceMatch ? "Source snippet found." : "Source snippet not found."));
          if (item.testNumber) row.append(element("p", "Test case " + item.testNumber + " · " +
            (statusText[item.testStatus] || "No grading result")));
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
      if (item.needle) row.append(element("p", "Source snippet found in submissions: " + item.sourceMatches), element("code", item.needle));
      if (item.testNumber) row.append(element("p", "Test case " + item.testNumber + " · " +
        item.testFailures + " failed / " + item.testObserved + " with results"));
      return row;
    }));
    if (configurationTask !== state.task?.id) {
      configurationTask = state.task?.id;
      publishedCases = state.task?.testCases || [];
      if (submissionDialog.open) submissionDialog.close();
      byId("teacher-case-config").replaceChildren(...publishedCases.map((test) => sampleBlock({
        ...test, name: test.name + (test.visibility === "hidden" ? " (hidden)" : " (public)"),
      })));
    }
    const stats = state.caseStats.map((test) => {
      const evaluated = test.passed + test.failed;
      const rate = evaluated ? "Pass rate: " + Math.round(100 * test.passed / evaluated) + "%" : "No test results yet";
      const title = test.name + (test.visibility === "hidden" ? " (hidden)" : " (public)");
      const causes = Object.entries(test.failureKinds).map(([key, count]) => statusText[key] + " " + count + (count === 1 ? " student" : " students"));
      return element("li", title + " · " + test.passed + " passed / " + test.failed + " failed · " + rate +
        (causes.length ? " (" + causes.join(", ") + ")" : ""));
    });
    byId("case-stats").replaceChildren(...stats);
    byId("no-errors").hidden = state.errorGroups.length > 0;
    const groups = state.errorGroups.map((group) => {
      const item = element("li");
      item.append(element("strong", (categoryText[group.category] || "Other compiler diagnostics") + " · " + group.count + (group.count === 1 ? " student" : " students")));
      if (group.example) item.append(element("pre", group.example));
      for (const message of group.repeatedMessages || []) {
        item.append(element("p", "Matching diagnostic · " + message.count + (message.count === 1 ? " student" : " students")),
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
        (statusText[key] || key) + " " + count + (count === 1 ? " student" : " students")).join(", ");
      item.append(element("strong", "Original line " + group.line + " · " + group.count + (group.count === 1 ? " student" : " students")),
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
      byId("room-name").textContent = next.name || "Classroom";
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
      byId("share-hint").textContent = "Scan the QR code or open the link to reach the student page. Select the code to enlarge it for projection.";
      qrButton.hidden = false;
    } catch {
      qrButton.hidden = true;
      byId("projection-qr").replaceChildren();
      byId("share-hint").textContent = "QR code unavailable. Copy the join link instead.";
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
      byId("projection-task").textContent = state.task?.title || "No task published yet";
      for (const metric of ["joined", "submitted", "accepted"]) {
        byId("projection-" + metric).textContent = state[metric];
      }
      const rate = state.joined ? Math.round(100 * state.submitted / state.joined) : 0;
      byId("projection-meter").value = rate;
      byId("projection-rate").textContent = state.joined ?
        state.submitted + " / " + state.joined + " submitted (" + rate + "%)" : "Waiting for students to join";
    }
    byId("projection-connection").textContent = "";
    byId("room-name").textContent = state.name;
    byId("current-task").textContent = state.task ?
      (archived ? "Earlier task · " : "Current task · ") + state.task.title : "No task published yet";
    for (const key of ["joined", "submitted", "attempts", "unsubmitted", "accepted", "failed", "queued", "pending", "unjudged"]) {
      byId(key).textContent = state[key];
    }
    byId("judge-state").textContent = state.executionAvailable ? "" :
      (state.queued ? "The judge is unavailable. Queued submissions have been saved and will resume when it reconnects." : "The isolated runner is unavailable. Ungraded submissions are excluded from the failure count.");
    const judged = state.accepted + state.failed;
    byId("class-pass-rate").textContent = judged ?
      "Pass rate for latest submissions: " + Math.round(100 * state.accepted / judged) + "% (based on " + judged + " students)" :
      "No completed grading results yet. A pass rate will appear after grading.";
    refreshStatus("Updates every 2 seconds");
    byId("empty-students").hidden = state.students.length > 0;
    const signature = JSON.stringify([archived, state.task?.id, state.students, state.caseStats, state.errorGroups, state.editPatterns, state.pitfallStats]);
    if (signature === analysisSignature) return;
    analysisSignature = signature;
    renderAnalysis(state);
    const rows = state.students.map((student) => {
      const row = document.createElement("tr");
      const status = state.task ? (student.count ? statusText[student.latestStatus] || "Unknown result" : "No submission") : "Waiting for a task";
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
      const praise = element("button", "Praise");
      praise.type = "button";
      praise.className = "secondary";
      praise.addEventListener("click", () => praiseStudent(student.name, student.number));
      const remove = element("button", "Remove");
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
      cell.textContent = "No students have joined yet";
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
      refreshStatus("Connection lost. Figures may be out of date.");
      byId("projection-connection").textContent = "Connection lost. Figures may be out of date.";
    }
  });

  const exportButton = byId("export-current-csv");
  exportButton.addEventListener("click", async () => {
    if (!credentials || exportButton.disabled) return;
    const roomId = credentials.id;
    const taskId = selectedTask.value;
    exportButton.disabled = true;
    exportButton.textContent = "Exporting…";
    feedback("", false, "export-feedback");
    try {
      const state = await api("/rooms/" + roomId + "/progress" + taskQuery(taskId), {
        headers: { "X-Teacher-Key": credentials.teacherKey }
      });
      if (credentials?.id !== roomId || selectedTask.value !== taskId) {
        feedback("The classroom or task changed. Export again.", true, "export-feedback");
        return;
      }
      if (!state.task) {
        feedback("Publish a task before exporting its results.", true, "export-feedback");
        return;
      }
      if (!Array.isArray(state.students) || state.students.length === 0) {
        feedback("No students have joined this classroom. There are no results to export.", true, "export-feedback");
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
      feedback("Exported current task results for " + state.students.length + (state.students.length === 1 ? " student." : " students."), false, "export-feedback");
    } catch (error) {
      feedback("Export failed: " + error.message, true, "export-feedback");
    } finally {
      exportButton.disabled = false;
      exportButton.textContent = "Export current task as CSV";
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
    feedback("Added “" + data.name + "”.", false, "schedule-feedback");
    await refresh();
  }, "schedule-feedback");

  onSubmit("publish", async (data) => {
    if (!credentials) return;
    if (composeMode === "prep" && notebook.hasPendingSelection()) {
      throw new Error("The selected cells are pending. Apply them to the starter code or remove them from the selection.");
    }
    if (!data.starterCode.trim() && !allowBlank.checked) {
      throw new Error("Enter starter code or select “Let students start with a blank editor”.");
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
    feedback("Task published: “" + data.title + "”. Student pages will update automatically.", false, "publish-feedback");
    await refresh();
  }, "publish-feedback");

  byId("copy-link").addEventListener("click", () => copyText(link, "copy-feedback", "Join link copied."));
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
    const time = new Date(item.receivedAt * 1000).toLocaleString("en");
    const score = item.total === undefined ? "" : " (" + item.passed + "/" + item.total + ")";
    return element("li", time + " · " + (statusText[item.status] || "Unknown status") + score);
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
      const title = typeof saved[id] === "string" ? saved[id] : "Classroom " + id.slice(0, 8);
      const row = element("li");
      if (id === currentRoom) {
        row.textContent = title + " (current classroom)";
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
    const button = element("button", "Copy result");
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
    fallback.setAttribute("aria-label", "Run result for manual copying");

    button.addEventListener("click", async () => {
      fallback.value = runResultCopyText(result);
      fallback.hidden = false;
      const copied = await copyText(fallback, "run-copy-feedback", "Run result copied.");
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
    byId("editor-feedback").textContent = currentTask && !archived ? "Latest task opened." : "";
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
      feedback("Task refresh failed. Retrying.", true, target);
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

  byId("copy-code").addEventListener("click", () => copyText(editor, "editor-feedback", "Code copied."));

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
    byId("stdin-label").textContent = interactive || active ? "Interactive standard input (stdin)" : "Complete standard input (batch)";
    byId("stdin-hint").textContent = interactive || active
      ? "Send one or more lines. The same process continues; select End input (EOF) to close stdin."
      : "Enter all required input before Run. This is batch execution: stdin closes after the supplied input. Leave blank for programs without input.";
    byId("run-state").textContent = active ? (live.status === "compiling" ? "Compiling…" : live.status === "stopping" ? "Stopping…" :
      "The process is running. You can send input; it may or may not be waiting for stdin.") :
      !enabled ? "Runner unavailable or historical task selected." :
      running ? "Compiling and running…" : interactive ? "Run starts a persistent process and does not count as a submission." :
      "Batch Run: enter complete stdin before running. This does not count as a submission.";
  }

  function showRunResult(result, active = false) {
    const panel = byId("run-result");
    panel.replaceChildren();
    displayResult(panel, result);
    if (Object.hasOwn(result, "exitCode")) panel.append(element("p", "Exit status " + result.exitCode));
    if (Object.hasOwn(result, "stdout")) panel.append(element("strong", "Standard output"), element("pre", result.stdout || (active ? "" : "(empty)")));
    if (result.stderr) panel.append(element("strong", "Standard error"), element("pre", result.stderr));
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
    if (Date.now() - run.started > 150000) {
      forgetLive();
      showRunResult({status: "request_error", error: "The execution session has exceeded its maximum lifetime. Run again."});
      return;
    }
    livePolling = true;
    const revision = run.revision || 0;
    try {
      const result = await sessionRequest(run, "poll");
      if (live === run && !liveAction && revision === (run.revision || 0)) {
        if (result.status === "judge_error" && !result.sessionId)
          byId("run-action-feedback").textContent = "Execution session connection unavailable; retrying.";
        else acceptLive(run, result);
      }
    } catch (error) {
      if (live === run) {
        if (error.status === 403 || error.status === 409) forgetLive();
        else byId("run-action-feedback").textContent = "Execution session connection unavailable; retrying.";
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
          byId("run-action-feedback").textContent = "Action not confirmed. Check the session state; input is not automatically resent.";
        else acceptLive(run, result);
      }
    } catch (error) {
      if (live === run) byId("run-action-feedback").textContent = "Action not confirmed: " + error.message + ". Check the output before deciding whether to retry.";
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
      optStatus.textContent = "Manual copy options are now available.";
      return;
    }
    // Preserve the teammate's one-click external tab flow; never embed OPT CPP.
    window.open(url, "_blank", "noopener,noreferrer");
  });
  byId("copy-opt-code").addEventListener("click", () => copyText(editor, "optcpp-status", "Current code copied."));

  byId("reset-code").addEventListener("click", () => {
    if (!currentTask) {
      feedback("No task is available to restore.", true, "editor-feedback");
      return;
    }
    if (!window.confirm("Discard your edits and restore the teacher's starter code?")) return;
    editor.value = currentTask.starterCode || "";
    saveEditorDraft("Starter code restored and draft updated.");
  });

  byId("download-code").addEventListener("click", () => {
    if (!currentTask) {
      feedback("No code is available to download.", true, "editor-feedback");
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
    byId("editor-feedback").textContent = "C++ code downloaded.";
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
      byId("editor-feedback").textContent = "Could not save your draft. Copy your code before refreshing.";
    }
  }

  editor.addEventListener("input", () => {
    if (!live && !running) {
      byId("run-result").hidden = true;
      byId("run-result").replaceChildren();
    }
    saveEditorDraft("Draft saved in this browser.");
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
      const run = {taskId, code, id: null, status: "compiling", stdinOpen: false, started: Date.now()};
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
      feedback("Saving code…", false, "submit-feedback");
      const receipt = await api(endpoint("/submissions"), { data: pendingSubmission, headers: headers() });
      pendingSubmission = null;
      if (taskId === currentTask?.id) {
        const message = receipt.judgement === "judge_unavailable" ?
          "Code saved. The isolated runner is unavailable, so this submission is ungraded." :
          receipt.judgement === "queued" || receipt.judgement === "pending" ?
            "Code saved. Grading progress appears below." :
          receipt.judgement === "judge_queue_full" ?
            "Code saved, but the grading queue is full. Try submitting again later." :
          receipt.judgement ? "Code saved · " + (statusText[receipt.judgement] || "Unknown status") :
            "Code submitted. Your teacher can see that it was received.";
        const receivedAt = Number(receipt.receivedAt);
        const submittedAt = Number.isFinite(receivedAt) && receivedAt > 0
          ? new Date(receivedAt * 1000)
          : new Date();
        const submittedTime = submittedAt.toLocaleString("en", {
          dateStyle: "medium",
          timeStyle: "short"
        });
        feedback(message + " Submitted at: " + submittedTime, false, "submit-feedback");
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
