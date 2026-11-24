const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const {compareLines} = vm.runInNewContext(fs.readFileSync(require.resolve("../web/diff.js"), "utf8") +
  "\n;({compareLines})");

const inputs = ["", "x", "x\n", "\n", "x\nx\ny", " x\n\ny", "x\r\ny", "<script>", "café"];
for (const original of inputs) {
  for (const revised of inputs) {
    const rows = compareLines(original, revised);
    for (const [column, source] of [["old", original], ["next", revised]]) {
      const visible = rows.filter(row => row[column] !== null);
      visible.forEach((row, index) => assert.equal(row[column], index + 1));
      assert.equal(visible.map(row => row.text).join("\n"), source.replace(/\r\n/g, "\n"));
    }
  }
}
const aligned = compareLines("a\nb\nc\nd", "new\na\nb\nd");
assert.equal(aligned.map(row => row.kind).join(""), "+  - ");
assert.equal(compareLines("a\n".repeat(1100), "b\n".repeat(1100)), null);
