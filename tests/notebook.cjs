"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { parse, parseCell } = require("../web/notebook.js");
const code = (source, metadata = {}) => ({cell_type:"code", source, metadata});
const md = (source, metadata = {}) => ({cell_type:"markdown", source, metadata});
const program = "int main() { return 0; }\n";
const mark = "// @classlab exercise\n";
const wrap = cells => ({nbformat:4, cells});
const read = cell => parseCell(cell, 4);
const base = {version:1, role:"exercise", title:"Metadata title", description:"Public specification",
  testCases:[{name:"Public",input:"",expectedOutput:"",visibility:"public"},{name:"Private",input:"secret",expectedOutput:"hidden",visibility:"hidden"}],
  pitfalls:[{name:"Boundary",note:"Teacher only",needle:"return",testNumber:"2"}]};
assert.equal(read(code(mark+program)).exercise.title, "ClassLab Exercise · Cell 5");
assert.equal(read(code(" \n%%cpp\r\n\n// @classlab exercise: Explicit title\r\n"+program,{classlab:base})).exercise.title,"Explicit title");
assert.equal(read(code(["%%cpp\n",mark,program],{classlab:base})).exercise.title,"Metadata title");
assert.equal(read(code(mark+program,{classlab:base})).exercise.testCases[1].visibility,"hidden");
assert.equal(read(code("%%cpp\n"+mark+program)).exercise.starterCode,mark+program);
assert.ok(read(code(mark+"int x=2;")).warning.includes("main"));
for(const fake of [
 md(mark+program), code('const char* text = "// @classlab exercise";\n'+program),
 code('auto s=R"(\n// @classlab exercise\n)";\n'+program),
 code('// general comment\n'+mark+program), code('/*\n'+mark+'*/\n'+program),
 code('// @classlab exercises\n'+program), code('// @classlab exercise in lecture\n'+program),
 code('%%hermes\n'+mark+program), code('%%cpp extra\n'+mark+program),
 code('%%python\n'+mark+program), code(mark+'%run helper\n'+program),
 code(mark+'%%python\n'+program), code(mark+'from __init__ import *\n'+program)
]) assert.equal(read(fake).exercise,null,JSON.stringify(fake));
for(const bad of [
 null, [], {version:2}, {role:"unknown"}, {referenceSource:program}, {title:123},
 {description:null}, {description:[]}, {testCases:null}, {testCases:[{name:"missing"}]},
 {testCases:[{name:"bad",input:"",expectedOutput:"",visibility:"private"}]},
 {pitfalls:[{name:"No such test",testNumber:"1"}]},
 {pitfalls:[{name:"Bad",needle:2}]}, {testCases:Array(13).fill(base.testCases[0])},
 {title:"x".repeat(54)}
]){
 const c=read(code(mark+program,{classlab:bad}));
 assert.equal(c.exercise,null,JSON.stringify(bad));assert.equal(c.protected,true);
}
for(const answer of [
 code("// @classlab answer\n"+program),
 code("%%cpp\n// @classlab reference: solution\n"+program),
 code(mark+program,{classlab:{role:"answer"}}),md("private answer",{classlab:{role:"reference"}})
]){assert.equal(read(answer).protected,true);assert.equal(read(answer).exercise,null);}
const ordinary = wrap([md("Introduction"),code("%%cpp\n"+program),{cell_type:"raw",source:"raw"},code(program)]);
assert.equal(parse(ordinary).count,0);
assert.equal(parse(ordinary).total,4);
assert.deepEqual(parse(ordinary).cells.map(c=>c.index),[0,1,3]);
const long = wrap(Array.from({length:135},(_,i)=>i%29===0 ? code(mark+program):code("%%cpp\n"+program)));
const copy=JSON.stringify(long);
assert.equal(parse(long).count,5);
assert.deepEqual(parse(long).cells.filter(c=>c.exercise).map(c=>c.index+1),[1,30,59,88,117]);
assert.equal(JSON.stringify(long),copy);
assert.throws(()=>parse({nbformat:3,cells:[]}));
const lecture=JSON.parse(fs.readFileSync(path.join(__dirname,"../examples/CS2310_Score_Analysis.ipynb"),"utf8"));
const parsed=parse(lecture);
assert.equal(parsed.count,5);assert.equal(parsed.total,74);assert.equal(parsed.warnings,0);
assert.deepEqual(parsed.cells.filter(c=>c.exercise).map(c=>c.index+1),[22,35,48,63,72]);
console.log("Notebook marker tests passed: strict prefix, titles, metadata validation, reference blocking, 135-cell input, backwards compatibility and original lecture.");
