# ClassLab development and review guide

## Project overview

ClassLab helps a teacher turn a C++ example from a notebook into a classroom debugging exercise. The teacher assembles selected Notebook cells, saves exercises locally with instructions, tests and anticipated pitfalls, then publishes to a classroom and shares its join QR code. Students use a browser to edit and submit, review their own recent attempts or open the optional external visualizer. The teacher can follow participation and, when adjudicated results exist, see which tests or compiler diagnostics are common across the class.

## Install and run

Use `main` to review the latest verified version and as the baseline for new work. Use the corresponding feature branch to review a specific development stage. Use Linux or WSL with a C++20 compiler, CMake 3.24 or later, Python 3, and network access to fetch the pinned C++ dependencies on the first build. CTest also runs the line-diff regression test when Node.js is available.

~~~sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure
~~~

Run the standard classroom server with ./build/classlab. Open http://127.0.0.1:8080 in the server's browser or open port 8080 through an existing private Codespaces preview. To demonstrate on another device, use the same preview URL with a GitHub account already authorized for that port.

## Student workflow

| Control | What it does |
| --- | --- |
| **恢复起始代码** (Restore starter code) | Confirm to replace the current editor contents with the teacher's starter for this task. The page also attempts to save the restored draft in this browser. |
| **下载 .cpp** (Download .cpp) | Save the current editor contents in a local .cpp file, named from the task title. |
| **运行代码** (Native Run-first) | Requires an available, security-accepted ClassLab Judge. Initially stdin stays hidden. The first run detects actual stdin consumption; if needed, the student enters the complete input and runs the program again from the beginning. This is not a live interactive terminal and does not count as a formal submission. |
| **提交代码** (Submit code) | Save a formal attempt. Ctrl+Enter or Command+Enter also submits from the editor. The receipt shows the submission time in the browser's local format and the initial status. A queued or ungraded receipt does not award a score. |
| **本题提交历史（最近 50 次）** (Current task submission history) | Expand to see your latest 50 attempts, newest first, with time, status and a score when available. The list follows the active task. The latest submission's details remain separate from the history. |

### OPT CPP practice

1. Click the original teammate-designed **抄送至OPT_CPP** button next to **复制代码**. It opens DIVE4DEC's OPT CPP visualizer in a new tab with the current editor contents and an empty input array. Its existing automatic display-mode behavior is unchanged.
2. Run and provide any requested input within OPT CPP itself. Use its step controls (including **Last**) to inspect the trace and output. ClassLab's native Run-first stdin is independent.
3. If the generated URL exceeds ClassLab's 8,192-character threshold, use **打开空白 OPT CPP** and **复制当前代码** to transfer the source manually.
4. If the external page or its runtime cannot load, keep editing, download a .cpp copy, or submit to ClassLab. Submission and classroom feedback remain available without the external tool. Judge results require an independently verified server installation.

**Privacy.** The address fragment is not included in the initial HTTP request, but the external page can read the code and any input supplied there, and the link may appear in local browser history or be shared. Do not pass passwords, tokens, personal data or private course materials. The external site's handling and policies apply. ClassLab does not receive the external output or award a score from it.

### Runtime and test boundaries

| Path | Execution and results |
| --- | --- |
| ClassLab Judge | The separately configured server Judge uses pinned GCC 14.3.0 in C++20 mode. It processes formal test outcomes only after the execution host passes the documented isolation acceptance. |
| OPT CPP link | DIVE4DEC's upstream documents an instrumented in-browser xeus-cpp / Clang-REPL WebAssembly runtime. Its trace, C++ features, diagnostics and I/O behavior can differ from GCC. For example, it exposes recorded steps and selected state, with limits on global tracing and debugger operations. See the [upstream documentation](https://github.com/dive4dec/OPT_CPP#limitations). |
| Official Python Tutor C++ service | The official [C++ Visualizer](https://pythontutor.com/cpp.html) is a separate endpoint. The reported GCC 9.3.0 / C++17 environment could not be independently confirmed against the live official service from the development environment. That version claim is not applied to OPT CPP. |

The Chromium handoff test intercepts the external request. With the regular ClassLab service running and Python Playwright installed, run:

~~~sh
python3 tests/browser_student.py http://127.0.0.1:8080 --executable /usr/bin/chromium
~~~

The integration check also ran the actual upstream assets from revision 654cd74 on loopback in Chromium. A C++ program read two stdin lines and produced RESULT=8, and an invalid program produced a compilation error. The live OPT CPP endpoint returned a proxy 403 from the cloud environment. Live access, Firefox and Safari execution were not verified.

## Repeatable classroom demonstration

Use the [authored score-analysis Notebook](../examples/CS2310_Score_Analysis.ipynb), publish Cell 22, join three separate browser sessions, correct the boundary and submit. Actual Run and grades require an accepted isolated Judge or a reviewed source in the trusted native experiment. Without it, demonstrate saved submissions and source changes only. See [the rehearsal guide](COURSEWORK_DEMO.md).

## Architecture and evidence

- The browser parses Notebook v4 files locally, supports code-cell sources stored as a string or an array, and publishes only the editor contents and task fields. Notebook metadata, outputs, and other cells stay on the device.
- The C++20 server handles classroom membership, role checks, submissions, the persistent queue, student-scoped attempt summaries and dashboard aggregation. Hidden tests stay within teacher-authorized paths, and the projection displays classroom totals.
- The normal Judge uses a private Unix socket and independent containers with a pinned GCC image. The execution service requires deployment acceptance before it can run arbitrary student programs. Phase 5 exercised real GCC with a trusted-source allowlist and verified results through the browser. Full runtime isolation acceptance for arbitrary submissions, including cgroup quotas and resource-exhaustion handling, remains outstanding.

## Development review and collaboration

| Criterion | Evidence and remaining handoff |
| --- | --- |
| Published | Share the private feature branch link and exact commit for review. Verify reviewer access. |
| Documented | English overview, setup, architecture, limitations and demo script are in this guide. Keep the guide current as the workflow changes. |
| Functional | Build and run CTest, rehearse the private classroom, distinguishing ungraded submissions from real GCC verdicts. Keep arbitrary execution disabled until isolation acceptance. |
| Innovative | The contribution is the lesson workflow from a notebook cell to immediate participation to class-level feedback. QR codes, compilation and test judging are established techniques. |
| Teamwork | Assign reviewers for the Notebook workflow, privacy checks, and rehearsal. Record only actual contributions. The Phase 5 baseline's Git author labels list seven commits under Thomas CAI and one under ThomasChoi2026. These figures describe the Phase 5 snapshot. The Git history records later contributors and their original commits. Record any confirmed offline work separately. |

Start each task from the latest `main` on a separate feature branch. Commit and push that branch, then share its GitHub compare link for review. Merge verified and reviewed changes into `main` with their history intact. Keep the existing history and author metadata. Record only confirmed contributors and reviewers.

## 60-second English demo script

Follow the current [Coursework Demo Guide](COURSEWORK_DEMO.md), using the full marked Score Analysis Notebook, not the legacy unmarked addition fixture.
