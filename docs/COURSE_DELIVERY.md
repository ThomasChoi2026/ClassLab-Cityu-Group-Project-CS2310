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

1. For input-based external exercises, expand **OPT CPP 标准输入（可选）** below the editor. This separate field stays optional and does not activate native Judge input. It is limited to 2,700 characters and resets on task changes.
2. Click the original teammate-designed **抄送至OPT_CPP** button next to **复制代码**. It opens DIVE4DEC's OPT CPP visualizer in a new tab with one click. The encoded fragment carries the current editor contents and the complete stdin text as a single entry in the JSON input array. Blank stdin uses an empty array. The visualizer can attempt to run immediately after opening.
3. Use the visualizer's step controls to inspect the trace. **Last** shows the final step and output. If the generated URL exceeds ClassLab's 8,192-character threshold, ClassLab shows **打开空白 OPT CPP** and separate copy buttons for the code and stdin. Use those controls to open a clean page and transfer the material manually.
4. If the external page or its runtime cannot load, keep editing, download a .cpp copy, or submit to ClassLab. Submission and classroom feedback remain available without the external tool. Judge results require an independently verified server installation.

**Privacy.** The address fragment is not included in the initial HTTP request, but the external page can read the code and input, and the link may appear in local browser history or be shared. Do not pass passwords, tokens, personal data or private course materials. The external site's handling and policies apply. ClassLab does not receive the external output or award a score from it.

### Runtime and test boundaries

| Path | Execution and results |
| --- | --- |
| ClassLab Judge | The separately configured server Judge uses pinned GCC 14.3.0 in C++20 mode. It processes formal test outcomes only after the execution host passes the documented isolation acceptance. |
| OPT CPP link | DIVE4DEC's upstream documents an instrumented in-browser xeus-cpp / Clang-REPL WebAssembly runtime. Its trace, C++ features, diagnostics and I/O behavior can differ from GCC. For example, it exposes recorded steps and selected state, with limits on global tracing and debugger operations. See the [upstream documentation](https://github.com/dive4dec/OPT_CPP#limitations). |
| Official Python Tutor C++ service | The official [C++ Visualizer](https://pythontutor.com/cpp.html) is a separate endpoint. The reported GCC 9.3.0 / C++17 environment could not be independently confirmed against the live official service from the development environment. That version claim is not applied to OPT CPP. |
| ClassLab demo | The demonstration uses clearly labelled fixed outcomes for bundled exercises. Classroom joins and submissions are real records in temporary storage. |

The Chromium handoff test intercepts the external request. With the regular ClassLab service running and Python Playwright installed, run:

~~~sh
python3 tests/browser_student.py http://127.0.0.1:8080 --executable /usr/bin/chromium
~~~

The integration check also ran the actual upstream assets from revision 654cd74 on loopback in Chromium. A C++ program read two stdin lines and produced RESULT=8, and an invalid program produced a compilation error. The live OPT CPP endpoint returned a proxy 403 from the cloud environment. Live access, Firefox and Safari execution were not verified.

## Repeatable classroom demo

1. Start python3 demo/run.py in the repository root. Use --port 8081 if 8080 is in use. Open the matching private preview. The demo generates a fresh temporary store for each launch. Press Ctrl+C to stop and remove it. The regular classroom data file is untouched.
2. Download the synthetic Notebook from the demo banner. Create a classroom and expand the Notebook importer. Choose the first code cell, then fill the starter code. Add title **Fix the addition** and instruction **Replace subtraction with addition**.
3. Click **填入三个演示用例** to load the three cases below. Publish the task and open Classroom View.

   | Name | Input | Expected output | Visibility |
   | --- | --- | --- | --- |
   | Positive | 2 3 | 5 | Public |
   | Zero | 0 0 | 0 | Public |
   | Mixed signs | -4 9 | 5 | Hidden |

4. Scan the QR code from a reachable classroom address, or open its join link on the same machine. Use three separate student browser sessions. Have one submit the starter unchanged and two change `a - b` to `a + b`. Expect one Wrong Answer and two Accepted replays. The second code cell can also demonstrate a Compilation Error. Other source or inputs display no matching fixture.
5. Return to management. Show the two passing students grouped under the same edit, open the sample submission, and point out the removed and added line. Contrast this with the unchanged submission and its failing cases. These are observations about the submitted code and recorded outcomes. Use synthetic student names for recording.

To rehearse in 60 seconds, download the synthetic file and have three browser sessions and their source snippets ready. Prefill the teacher’s title, instructions and test cases before recording, then select the cell and publish on camera. Keep the live join and submission actions visible.

For an optional automated browser rehearsal, leave the demo running and use a second terminal with Python, Playwright, Pillow and zxing-cpp installed. Run `python3 tests/browser_demo.py http://127.0.0.1:8080 --chromium /path/to/chromium`. The test decodes the displayed QR image, joins three fresh browser sessions, restores a draft after reload, submits the exercise, and checks the teacher counts and line diff. The standard build and CTest suite do not require these browser packages.

## Architecture and evidence

- The browser parses Notebook v4 files locally, supports code-cell sources stored as a string or an array, and publishes only the editor contents and task fields. Notebook metadata, outputs, and other cells stay on the device.
- The C++20 server handles classroom membership, role checks, submissions, the persistent queue, student-scoped attempt summaries and dashboard aggregation. Hidden tests stay within teacher-authorized paths, and the projection displays classroom totals.
- The normal Judge uses a private Unix socket and independent containers with a pinned GCC image. The execution service requires deployment acceptance before it can run arbitrary student programs. Phase 5 exercised real GCC with a trusted-source allowlist and verified results through the browser. Full runtime isolation acceptance for arbitrary submissions, including cgroup quotas and resource-exhaustion handling, remains outstanding.
- Demo mode records real joins, edits and submissions against a temporary store. It replays fixed results for the published synthetic exercise. It disables free-form execution and labels replay results on both sides. It works without Docker, a compiler in the browser, student credentials, or external services at runtime.

## Development review and collaboration

| Criterion | Evidence and remaining handoff |
| --- | --- |
| Published | Share the private feature branch link and exact commit for review. Verify reviewer access. |
| Documented | English overview, setup, architecture, limitations and demo script are in this guide. Keep the guide current as the workflow changes. |
| Functional | Build and run CTest, rehearse the private demo, and distinguish the replay from the prior real GCC evidence. Keep arbitrary execution disabled until isolation acceptance. |
| Innovative | The contribution is the lesson workflow from a notebook cell to immediate participation to class-level feedback. QR codes, compilation and test judging are established techniques. |
| Teamwork | Assign reviewers for the Notebook workflow, privacy checks, and rehearsal. Record only actual contributions. The Phase 5 baseline's Git author labels list seven commits under Thomas CAI and one under ThomasChoi2026. These figures describe the Phase 5 snapshot. The Git history records later contributors and their original commits. Record any confirmed offline work separately. |

Start each task from the latest `main` on a separate feature branch. Commit and push that branch, then share its GitHub compare link for review. Merge verified and reviewed changes into `main` with their history intact. Keep the existing history and author metadata. Record only confirmed contributors and reviewers.

## 60-second English demo script

| Time | Show | Say |
| --- | --- | --- |
| 0–10 s | Teacher editor and synthetic Notebook | “A teacher already has an example in a notebook. Turning it into a shared debugging task usually breaks the flow of the lesson. ClassLab keeps that workflow in one place.” |
| 10–23 s | Select the buggy cell, publish, then open Classroom View | “I choose a C++ cell, add instructions and test cases, and publish it. The notebook stays in my browser. Students get the selected exercise through this QR code.” |
| 23–38 s | Student views and their code changes | “Students join from a browser, edit the exercise, and submit. The projection updates as their submissions arrive.” |
| 38–53 s | Common edit and line diff | “Two students changed subtraction to addition. Here is the line they edited and the test result for each submission. The verdicts are fixed replays. The submissions and class counts are live.” |
| 53–60 s | Return to Classroom View | “The goal is to help the teacher decide what to explain next while the class is still working.” |
