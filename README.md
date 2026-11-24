# ClassLab

**Turn C++ lecture notebooks into interactive classrooms.**

City University of Hong Kong · CS2310 Computer Programming · Agentic Coding Group Project

ClassLab helps teachers turn selected examples in their existing Jupyter Notebooks into live programming exercises. Students join by QR code, edit and submit C++ in a browser, and teachers review the class's progress, common code changes and test outcomes before moving on to the next concept.

[Try the classroom demo](#quick-start) · [Download the teaching Notebook](examples/CS2310_Score_Analysis.ipynb) · [Browser demonstration evidence](#testing-and-evidence) · [Documentation](#documentation) · [Team](#team-contributions)

## Why ClassLab?

A lecture Notebook may contain hundreds of cells, but only a handful need student participation. Finding those examples, distributing code and collecting individual responses can interrupt the flow of a lesson.

ClassLab connects **Notebook preparation, interactive coding and classroom feedback** in one workflow. Teachers can mark exercises during preparation, select them during class and use students' submissions to identify topics that need further explanation. It complements existing C++ visualizers and judges rather than replacing them.

## Key features

| Feature | What ClassLab provides |
| --- | --- |
| Notebook integration | Direct .ipynb import, automatic exercise recognition, search, cell preview and optional multi-cell code assembly. |
| Lesson preparation | Marked exercises with optional descriptions, public/hidden tests and expected pitfalls; locally saved drafts and a quick code-paste mode. |
| Live classroom | Explicit task publication, QR/link joining, classroom projection and consecutive exercises without re-importing the Notebook. |
| Student workspace | C++ editing, independent Run and Submit, on-demand stdin, output/diagnostic copying, starter reset, .cpp download and one-click external OPT CPP handoff. Native Run requires an accepted Judge. |
| Classroom analytics | Participation, submission status, source differences, shared code edits, test outcomes, pitfall evidence and current-task CSV export. |
| Classroom management | Previous classrooms and tasks, student removal and praise, submission history, and a weekly timetable with overlap detection. |

## How ClassLab works

1. **Prepare.** The teacher opens Lesson Preparation (the default workspace), imports a Notebook and selects a marked exercise. Quick Classroom is also available for ad-hoc code.
2. **Publish.** ClassLab loads the exercise's starter code and any preset instructions, tests and pitfalls. The teacher reviews the editor and explicitly publishes the task.
3. **Join and practise.** Students follow a QR code or join link, edit their own code, run it when execution is available, and submit an attempt.
4. **Review.** The teacher sees live participation and submissions, compares code changes, and reviews available test results. These are teaching clues, not proof of a student's reasoning.
5. **Continue.** Publish the next exercise from the same Notebook, revisit earlier tasks or export the selected task's results as CSV.

The teacher's built-in usage guide explains the main controls. A loaded Notebook remains available within the current page; reloading or closing it requires another import. Saved lesson drafts and classroom access keys are retained in the browser, independently of the server's classroom records.

### Try the original teaching material

[**CS2310 — From Control Flow to Procedural Abstraction (.ipynb)**](examples/CS2310_Score_Analysis.ipynb)

An original 74-cell lecture about score analysis, including 22 ordinary teaching programs and five marked exercises. On GitHub, open the file and choose **Download raw file**.

| Cell | Interactive exercise | Learning objective |
| ---: | --- | --- |
| 22 | Fix the grade boundary | Conditional boundaries |
| 35 | Debug the accumulation loop | Loop iteration counts |
| 48 | Find the maximum correctly | Array traversal and initialization |
| 63 | Fix the average function | Numeric types and integer division |
| 72 | Complete the score analyser | Function decomposition and transfer |

The separate [instructor references](examples/score_analysis_references.json) contain the sample solutions and replay data. Do not distribute private teaching material or reference answers to students.

## Quick start

The same repository provides two independently launched modes. No Docker installation or paid server is required to try the classroom workflow.

| Mode | Classroom activity | Execution and grading | Data |
| --- | --- | --- | --- |
| Demo (8082) | Real joining, editing, submissions and feedback | Clearly labelled, fixed replay for the five sample exercises | Temporary |
| Normal (8080) | Real classroom activity and records | Native C++20 Run and grading require a validated isolated Judge; submission-only otherwise | Persistent |

### 1. Get the project

Use Linux, WSL or a Linux GitHub Codespace with Git, CMake 3.24+, a C++20 compiler, Python 3 and Node.js (for the complete test suite). The first build needs internet access to fetch pinned dependencies.

For a fresh checkout:

~~~bash
git clone --branch main https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310.git
cd ClassLab-Cityu-Group-Project-CS2310
~~~

In an existing Codespace, use the repository terminal instead of cloning again.

### 2. Choose a mode

**Demo — recommended for coursework review**

~~~bash
bash demo/start_coursework.sh 8082
~~~

The script builds the application, runs the automated tests and launches a temporary classroom. Open http://127.0.0.1:8082. No native Judge is launched.

**Normal — for ordinary classroom use**

~~~bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
CLASSLAB_DEMO=0 CLASSLAB_HOST=127.0.0.1 CLASSLAB_PORT=8080 CLASSLAB_JUDGE_SOCKET= ./build/classlab
~~~

Open http://127.0.0.1:8080. This command deliberately starts without a Judge: submissions, analytics and external OPT CPP remain available, but native Run and grading are unavailable. To enable real execution, follow the [administrator setup](docs/RUN_CLASSLAB.md) and [isolation acceptance guide](docs/PHASE_4.md).

**Using Codespaces:** Open the Ports panel, forward the chosen port (8082 or 8080), keep it **Private**, and select Open in Browser. The generated join link uses the forwarded address; other devices need authorized access to the private preview. Stop the server with Ctrl+C. See [Running ClassLab](docs/RUN_CLASSLAB.md) for detailed setup and troubleshooting.

### 3. Rehearse a classroom in one minute

Download the [sample Notebook](examples/CS2310_Score_Analysis.ipynb), then use Demo Mode:

1. Create a classroom, upload the Notebook in Lesson Preparation and select **Fix the grade boundary — Cell 22**. Five interactive exercises are recognized among the 74 cells.
2. Review the prefilled task and test cases (three public, two hidden), then publish.
3. In a separate student session, use the join link. Click Demo Run, provide the public input `60`, and view the prerecorded `FAIL`.
4. Change only `score > 60` to `score >= 60`, run with the same input and view `PASS`.
5. Submit the starter from one student and the exact corrected code from two others. Review the resulting 2 accepted / 1 failed dashboard and shared edit, then select the next exercise.

The classroom records and code comparisons are live. **Demo results are replay, not live compilation.** Other source variants or inputs may have no matching fixture, even if the program is correct.

[Full rehearsal and 60-second English script](docs/COURSEWORK_DEMO.md)

## Bring your own Notebook

In a C++ Code cell, add this case-sensitive comment as the first nonblank line:

~~~cpp
// @classlab exercise: Fix the grade boundary
#include <iostream>

int main() {
    int score;
    std::cin >> score;
    std::cout << (score > 60 ? "PASS" : "FAIL") << '\n';
}
~~~

Save the .ipynb file and upload it in Lesson Preparation. ClassLab automatically identifies marked cells; unmarked teaching examples remain available for manual preview and insertion. If your kernel uses a bare `%%cpp`, put the marker immediately after it. The title is optional.

- **Optional metadata:** Preload the task description, up to 12 public/hidden tests and up to 8 expected pitfalls using `metadata.classlab`. These can also be configured in the editor. A task without tests can still collect submissions.
- **Explicit publication:** Selecting or importing a cell never publishes automatically. Review the actual starter code; an intentionally blank task requires an explicit choice.
- **Teacher-only material:** Keep solutions separate or use `// @classlab answer` (or the documented reference role). Hidden test contents and teacher pitfalls are excluded from student-facing task data. Do not put private material in public fields.

See the [complete marker and Metadata guide](docs/NOTEBOOK_CLASSROOM.md) for syntax, validation, authoring examples and unsupported Notebook commands.

## Architecture

~~~text
Teacher browser                    Student browsers
Notebook parser / exercise editor  C++ editor / Run / Submit
                   \                 /
                   HTTP classroom API
                            |
                   C++20 ClassLab server
              Records / queue / analytics
                            |
                     Private Unix socket
                    /                  \
        Normal: isolated Judge      Demo: fixed fixtures
        (validated host required)   (no arbitrary execution)
~~~

| Path | Responsibility |
| --- | --- |
| `web/` | Browser interfaces, Notebook parsing, QR codes and code comparison |
| `src/` | C++20 server, role-specific access, classroom persistence and grading queue |
| `judge/` | Independent GCC/Docker execution worker with isolation checks |
| `demo/` and `examples/` | Labelled replay launcher and original teaching materials |
| `tests/` | CTest, trusted C++ fixtures and Playwright browser acceptance |

The server uses cpp-httplib and nlohmann/json; the frontend uses HTML, CSS and JavaScript without a separate build step. Native Run-first probes whether input is consumed and reruns from the beginning with complete stdin when required; it is not a live interactive terminal. OPT CPP is an external new-tab link, not an embedded runtime or a source of ClassLab grades.

## Testing and evidence

~~~bash
ctest --test-dir build --output-on-failure
~~~

- [Latest reviewed full Notebook/classroom acceptance (PR #22)](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/actions/runs/45387803276): successful C++20 build, CTest, student/teacher browser regressions, Run-first, consecutive publication and marked-Notebook rehearsal.
- [Browser screenshots from that acceptance run](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/actions/runs/45387803276/artifacts/14917012193): actual UI evidence, subject to GitHub access and artifact retention.
- [CSV export and Run output copy acceptance (PR #20)](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/actions/runs/45382104544).
- [Lecture and marker integration acceptance (PR #16)](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/actions/runs/45361246934): 11/11 CTest tests at that revision, including 27 code cells, five reference implementations and 23 verified exercise cases.
- [All GitHub Actions workflows](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/actions).

These checks establish the tested classroom workflows and trusted fixtures. They do not establish that arbitrary student C++ can safely execute on every host.

## Deployment and current limitations

ClassLab is a coursework prototype for small, trusted classrooms, not a public production service.

- Native C++20 execution and automatic grading are implemented but require a dedicated compatible Linux host and a Judge that passes the documented isolation and resource-limit acceptance. Full production-host acceptance remains outstanding; a Codespace with Docker is not sufficient evidence.
- Without an accepted Judge, Normal Mode still collects real submissions. Demo Mode only replays supported sample variants and inputs; it never falls back to unisolated execution.
- Nicknames are not verified accounts. Keep browser access keys and back up the Normal Mode classroom store. CSV export covers the selected task, not an entire semester.
- External OPT CPP receives the source passed to it; supply any stdin directly there and avoid sending sensitive material.
- Do not expose the Demo service or Judge socket publicly, or bypass the execution safety checks.

[Administrator setup and environment variables](docs/RUN_CLASSLAB.md) · [Native Judge isolation acceptance](docs/PHASE_4.md)

## Team contributions

The following six CS2310 team accounts have contributions traceable to the repository's commits and pull requests.

| Team member | Actual contribution |
| --- | --- |
| [ThomasChoi2026](https://github.com/ThomasChoi2026) | Classroom MVP, Notebook preparation and integration; requirements and prompts for classroom analysis and code comparison. |
| [aries36white](https://github.com/aries36white) | One-click student-editor handoff to external OPT CPP. [PR #3](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/3) |
| [superlulu77](https://github.com/superlulu77) | Starter reset, .cpp download, timestamped receipts, current-task CSV export and copying Run output/diagnostics. [PR #1](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/1), [PR #20](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/20) |
| [godferywong098kirito-blip](https://github.com/godferywong098kirito-blip) | Student submission history. [PR #2](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/2) |
| [Mizunonamae](https://github.com/Mizunonamae) | Teacher classroom controls, student removal and praise, and macOS build fix. [PR #4](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/4) |
| [isferr](https://github.com/isferr) | Weekly timetable and schedule overlap detection. [PR #5](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/5) |

[Classroom MVP commit](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/commit/4fb68b0921305a08e3cad88a62193acf9f17237e) · [Notebook lesson preparation commit](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/commit/a7dda8450da2b95796ecc2d80550e4aaa537a7d5) · [Complete main history](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/commits/main/)

## Documentation

| Guide | Purpose |
| --- | --- |
| [Running ClassLab](docs/RUN_CLASSLAB.md) | Normal, Demo and school-server setup |
| [Notebook classroom integration](docs/NOTEBOOK_CLASSROOM.md) | Markers, Metadata and teacher-only material |
| [Coursework demonstration](docs/COURSEWORK_DEMO.md) | Rehearsal and presentation script |
| [Course delivery](docs/COURSE_DELIVERY.md) | Detailed teacher/student controls and architecture |
| [Native Judge acceptance](docs/PHASE_4.md) | Isolation requirements and deployment verification |
| [Project context](docs/PROJECT_CONTEXT.md) | Development context and handoff |

## Acknowledgements

We thank our CS2310 instructor, **Professor Chung Chan**, for developing [OPT CPP](https://github.com/dive4dec/OPT_CPP) ([initial author credit](https://github.com/dive4dec/OPT_CPP/commit/f8b60a93e15139831546a4e4d7c37a39fe217354)), the external C++ visualizer linked from ClassLab. OPT CPP builds on the visualization work of **Philip J. Guo**, creator of [Python Tutor](https://pythontutor.com/).

ClassLab independently implements its classroom workflow, editor handoff, submission history, teacher analytics and Judge integration. It ships no OPT CPP/Python Tutor source or WASM assets. Attribution does not imply participation, sponsorship or endorsement.

Third-party dependencies: [qrcode-generator 1.4.4 (MIT notice)](web/vendor/qrcode.LICENSE), [cpp-httplib v0.28.0 (MIT)](https://github.com/yhirose/cpp-httplib/tree/v0.28.0), and [nlohmann/json v3.12.0 (MIT)](https://github.com/nlohmann/json/tree/v3.12.0).

Further references: [Python Tutor C++ visualizer](https://pythontutor.com/cpp.html), [link integration guide](https://pythontutor.com/for-ai-assistants.html), and Guo, P. J. (2013), *Online Python Tutor: Embeddable Web-Based Program Visualization for CS Education*, SIGCSE '13, 579–584. [DOI: 10.1145/2445196.2445368](https://doi.org/10.1145/2445196.2445368).
