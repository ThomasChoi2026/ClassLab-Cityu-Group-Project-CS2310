"use strict";

// Line numbers start at one. An empty final row represents a trailing newline.
function compareLines(original, submission) {
  const split = (text) => text ? text.replace(/\r\n/g, "\n").split("\n") : [];
  const before = split(original);
  const after = split(submission);
  let start = 0, aEnd = before.length, bEnd = after.length;
  while (start < aEnd && start < bEnd && before[start] === after[start]) ++start;
  while (aEnd > start && bEnd > start && before[aEnd - 1] === after[bEnd - 1]) {
    --aEnd;
    --bEnd;
  }
  const m = aEnd - start, n = bEnd - start;
  // For exceptionally large rewrites show both originals instead of guessing an alignment.
  if ((m + 1) * (n + 1) > 1000000) return null;
  const stride = n + 1;
  const lengths = new Uint32Array((m + 1) * stride);
  for (let i = m - 1; i >= 0; --i) {
    for (let j = n - 1; j >= 0; --j) {
      const k = i * stride + j;
      lengths[k] = before[start + i] === after[start + j] ? 1 + lengths[k + stride + 1] :
        Math.max(lengths[k + stride], lengths[k + 1]);
    }
  }
  const rows = [];
  let i = 0, j = 0;
  function emit(kind) {
    const text = kind === "+" ? after[j] : before[i];
    rows.push({kind, old: kind === "+" ? null : ++i, next: kind === "-" ? null : ++j, text});
  }
  while (i < start) emit(" ");
  while (i < aEnd || j < bEnd) {
    const k = (i - start) * stride + j - start;
    if (i < aEnd && j < bEnd && before[i] === after[j]) emit(" ");
    else if (j === bEnd || (i < aEnd && lengths[k + stride] >= lengths[k + 1])) emit("-");
    else emit("+");
  }
  while (i < before.length) emit(" ");
  return rows;
}
