/* Pure Notebook v4 classroom marker parser; shared by browser and Node tests. */
"use strict";
(function (root) {
  const object = v => v !== null && typeof v === "object" && !Array.isArray(v);
  const bytes = s => new TextEncoder().encode(s).length;
  const str = (v, chars, limit, nonempty = false) =>
    typeof v === "string" && v.length <= chars && bytes(v) <= limit && (!nonempty || v.trim().length > 0);
  const fields = (v, names) => object(v) && Object.keys(v).every(k => names.includes(k));
  const firstLine = s => s.trimStart().split(/\r?\n/, 1)[0];
  const titlePattern = /^\/\/[ \t]*@classlab[ \t]+exercise(?:[ \t]*:[ \t]*(.+?))?[ \t]*$/;
  function parseCell(raw, index) {
    if (!object(raw) || !["code", "markdown"].includes(raw.cell_type)) return null;
    const code = typeof raw.source === "string" ? raw.source :
      Array.isArray(raw.source) && raw.source.every(s => typeof s === "string") ? raw.source.join("") : null;
    if (code === null) return null;
    const cell = {index, code, kind: raw.cell_type, exercise: null, protected: false, warning: ""};
    const fail = message => { cell.warning = message; cell.protected = true; return cell; };
    const meta = raw.metadata?.classlab;
    if (meta !== undefined && (!fields(meta, ["version", "role", "title", "description", "testCases", "pitfalls"]) ||
        (meta.version !== undefined && meta.version !== 1) ||
        (meta.role !== undefined && !["exercise", "answer", "reference"].includes(meta.role)))) {
      return fail("Invalid ClassLab metadata. Loading this cell is blocked to protect its contents.");
    }
    let source = code.replace(/^\uFEFF/, "").trimStart();
    const first = firstLine(source);
    const magic = /^%%cpp[ \t]*$/.test(first);
    if (magic) source = source.slice(first.length).replace(/^\r?\n/, "").trimStart();
    if (meta?.role === "answer" || meta?.role === "reference" ||
        (cell.kind === "code" && /^\/\/[ \t]*@classlab[ \t]+(?:answer|reference)(?:[ \t]*:.*)?[ \t]*$/.test(firstLine(source)))) {
      return fail("Teacher reference cell: preview only. It cannot be loaded, combined, or added to student instructions.");
    }
    if (cell.kind !== "code") {
      if (meta !== undefined) return fail("Exercise markers are only valid in C++ code cells.");
      return cell;
    }
    const marker = firstLine(source).match(titlePattern);
    if (!marker) {
      if (meta !== undefined) return fail("ClassLab metadata requires a valid exercise marker at the beginning of the cell.");
      return cell;
    }
    if (marker[1] !== undefined && !marker[1].trim()) return fail("Add a title after the exercise marker's colon or omit the colon.");
    // Exact %%cpp is the only removable magic. Keep C++ text verbatim except
    // the wrapper and leading whitespace. The marker itself remains a comment.
    const body = source.slice(firstLine(source).length).trim();
    if (!body || /^(?:[ \t]*[%!]|[ \t]*(?:from\s+\S+\s+import\s+|import\s+\w+|def\s+\w+\s*\())/m.test(body) ||
        !/(?:#\s*include\s*[<"]|\b(?:int|void|double|float|char|bool|auto|class|struct|template|constexpr|using|std::|cin|cout)\b|[;{}])/.test(body) ||
        !str(source, 20000, 65536, true)) {
      return fail("This exercise contains an unsupported notebook directive, appears to use another language, or exceeds the source length limit.");
    }
    const title = marker[1]?.trim() || meta?.title || "ClassLab Exercise · Cell " + (index + 1);
    const description = meta?.description ?? "";
    const testCases = meta?.testCases ?? [];
    const pitfalls = meta?.pitfalls ?? [];
    if (!str(title, 53, 160, true) || (meta?.title !== undefined && !str(meta.title, 53, 160, true)) ||
        !str(description, 3000, 10000) || !Array.isArray(testCases) || testCases.length > 12 ||
        !Array.isArray(pitfalls) || pitfalls.length > 8 ||
        (meta && ["description", "testCases", "pitfalls"].some(k => Object.hasOwn(meta, k) && meta[k] === null))) {
      return fail("Invalid format or length for the exercise title, description, test cases, or pitfall metadata.");
    }
    if (!testCases.every(t => fields(t, ["name", "input", "expectedOutput", "visibility"]) &&
        str(t.name, 40, 120, true) && str(t.input, 2700, 8192) && str(t.expectedOutput, 2700, 8192) &&
        ["public", "hidden"].includes(t.visibility))) {
      return fail("Check the notebook's test cases for missing fields, length limits, and valid visibility settings.");
    }
    if (!pitfalls.every(p => fields(p, ["name", "note", "needle", "testNumber"]) &&
        str(p.name, 60, 240, true) && str(p.note ?? "", 300, 1200) && str(p.needle ?? "", 160, 640) &&
        (p.needle == null || p.needle === "" || p.needle.trim()) &&
        (p.testNumber === undefined || p.testNumber === "" ||
         (typeof p.testNumber === "string" && /^(?:[1-9]|1[0-2])$/.test(p.testNumber) && Number(p.testNumber) <= testCases.length)) &&
        ["note", "needle", "testNumber"].every(k => !Object.hasOwn(p, k) || typeof p[k] === "string"))) {
      return fail("Invalid pitfall metadata or reference to a missing test case.");
    }
    cell.exercise = {title, description, starterCode: source, testCases, pitfalls};
    if (!/\bmain\s*\(/.test(source)) cell.warning = "No main() found. If this is a fragment, add dependencies and an entry point before publishing.";
    return cell;
  }

  function parse(notebook) {
    if (notebook?.nbformat !== 4 || !Array.isArray(notebook.cells)) throw Error("Invalid Notebook v4");
    const cells = notebook.cells.map(parseCell).filter(Boolean);
    return {cells, total: notebook.cells.length, count: cells.filter(c => c.exercise).length,
            warnings: cells.filter(c => c.protected && c.warning && !c.warning.startsWith("Teacher reference cell")).length};
  }
  const api = {parse, parseCell};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.ClassLabNotebook = api;
})(globalThis);
