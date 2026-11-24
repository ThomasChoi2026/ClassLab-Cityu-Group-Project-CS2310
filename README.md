# ClassLab

**Turn C++ lecture notebooks into interactive classroom exercises.**

City University of Hong Kong · CS2310 Computer Programming · Agentic Coding Group Project

ClassLab connects a teacher's existing Jupyter Notebook to a live classroom. Teachers select exercises, publish starter code and tests, and share a QR code. Students edit and submit C++ in their browsers. The teacher can then inspect common code changes, test failures and class participation to decide what to explain next.

The project's distinctive contribution is this **Notebook → exercise → student submissions → classroom feedback** workflow. It complements existing C++ visualizers and automated judges rather than recreating them.

[Quick Start](#quick-start) · [Classroom Demo](#one-minute-classroom-demo) · [Teacher Guide](#teacher-workflow) · [Student Guide](#student-workflow) · [Testing](#testing-and-evidence) · [Team](#team-contributions)

## Download the sample Notebook before starting

[**Get the sample Notebook (.ipynb)**](examples/CS2310_Score_Analysis.ipynb) on GitHub. Choose **Download raw file** to save it before opening ClassLab. The file contains 74 cells and five marked exercises.

Import the file through **课前备课 (Lesson Preparation)**. The sample remains a teaching resource, not a replay mechanism. This branch retains the isolated Judge; native execution requires a validated host. To prepare your own file, see [marking a Notebook exercise](#notebook-classroom-integration) and the [authoring guide](docs/NOTEBOOK_CLASSROOM.md).

## Quick Start

### 1. Build once

Use Linux, WSL or a Linux GitHub Codespace. Requirements: Git, CMake 3.24+, a C++20 compiler (such as GCC), and Python 3. Node.js is needed for the complete test suite. The first build requires internet access to fetch pinned dependencies. No separate frontend build is required.

For a fresh checkout:

~~~bash
git clone --branch fix/sandbox-interactive-stdin https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310.git
cd ClassLab-Cityu-Group-Project-CS2310
~~~

If you already have the repository open in Codespaces, use its terminal in the repository root instead of cloning it again. Ensure the checkout contains the desired branch revision before building; preserve any uncommitted work.

~~~bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
~~~

### 2. Start the classroom (port 8080)

~~~bash
CLASSLAB_HOST=127.0.0.1 CLASSLAB_PORT=8080 CLASSLAB_JUDGE_SOCKET= ./build/classlab
~~~

Open **http://127.0.0.1:8080** on the same machine, or use the private Codespaces preview for port **8080**.

Create a classroom, import a Notebook or paste any C++ starter code, and collect actual student submissions. Classroom data persists in `data/classrooms.json` by default.

**The command above deliberately launches without a Judge.** Code submission, class progress and source comparison still work. Native Run and automatic grading require a separately installed and security-accepted Judge (see [Judge deployment](docs/PHASE_4.md)). The external OPT CPP link remains available.

### 3. Open the correct page in Codespaces

1. Select this branch in GitHub and build the project in its Codespace.
2. Keep port 8080 **Private** and open it in the browser. Other devices need access to that private preview.
3. Stop the server with Ctrl+C. Never forward the Judge socket.

## One-minute classroom demo

Use the sample Notebook (74 cells, five exercises). Publish Cell 22, join three student sessions, correct `score > 60` to `score >= 60`, and submit. With an accepted Judge the public input `60` produces `FAIL` then `PASS`, and the classroom shows actual verdicts. Without a Judge, show source differences and submission counts; do not claim grading. See [rehearsal guide](docs/COURSEWORK_DEMO.md).

## Teacher workflow

| Stage | What the teacher does |
| --- | --- |
| Prepare | Choose **快速课堂 (Quick Classroom)** to paste C++, or **课前备课 (Lesson Preparation)** to import a Notebook and manage locally saved exercises. |
| Configure | Enter a title and provide starter code or choose **让学生从空白开始**. The description, up to 12 public or hidden test cases, and up to 8 expected pitfalls are optional. |
| Publish | Review the editor and publish explicitly; importing or selecting a Notebook cell does not publish a task. |
| Share | Invite students using the join link or QR code; switch to classroom projection for a simplified class display. |
| Review | Inspect each student's latest submission, source diff, test outcomes, shared edits and pitfall evidence. Use them as review clues, not proof of a student's reasoning. |
| Continue | Publish the next exercise without re-uploading. The Notebook stays available in the current page, while the editor clears and the dashboard switches to the active task. Reloading or closing the page requires re-importing the Notebook. |

Additional teacher controls include praise, student removal and a weekly timetable with overlap detection. The lesson library saves drafts in the current browser; it is independent of server-side classroom records. After publishing multiple tasks, select **查看已发布任务** in Classroom Progress to inspect earlier submissions, code differences and test statistics. The selection only changes the teacher view. The classroom projection shows the latest task. **切换已管理的课堂** lets teachers return to any classroom whose access key is still saved in this browser. Creating a new classroom keeps those keys and records.

### Notebook classroom integration

In Jupyter, create a **Code** cell and add the marker on its first nonblank line. If the cell starts with a bare `%%cpp`, put the marker on the first nonblank line after it:

~~~cpp
// @classlab exercise: Fix the grade boundary
#include <iostream>

int main() {
    int score;
    std::cin >> score;
    if (score > 60) std::cout << "PASS\n";
    else std::cout << "FAIL\n";
}
~~~

The marker is a case-sensitive C++ comment. Use a colon (`:`) before a custom title. You can omit both the colon and title with `// @classlab exercise`. The importer uses the title from Cell Metadata if provided, then falls back to the original Cell number. The marker itself needs no semicolon.

Save as `.ipynb`, then import it in **课前备课**. ClassLab detects marked exercises, shows their count and loads the chosen exercise into the editor. Review the fields and use **发布为当前任务** to share it. Unmarked cells remain available for browsing and manual insertion.

**Preloading tests and pitfalls is optional.** The sample includes them for demonstration. For your own marked exercise, the marker and C++ code are enough. You may omit the entire `metadata.classlab` object, or include only the fields you need. You can also add a description, tests or pitfalls in the teacher editor after importing. A task without test cases can still be published and collect submissions. A task without expected pitfalls skips that comparison. When linking a pitfall to a test, use an existing test number. For an example you can copy, see [preload tests and pitfalls before class](docs/NOTEBOOK_CLASSROOM.md#preload-tests-and-pitfalls-before-class).

The Notebook is parsed locally in the teacher browser (Notebook v4, up to 2 MiB). Ordinary cells are previewed before insertion; marked exercises load their preset fields. Draft replacement requires confirmation when necessary. The teacher must publish explicitly; the app blocks an unintended empty starter or uninserted code combination. Advanced combination, test settings and the lesson library are collapsed by default. Mark teacher reference cells with `// @classlab answer` or Metadata role `answer` / `reference` so the import controls cannot insert them into a student task. Keep private answers and hidden inputs out of the public description and starter code; do not distribute a teacher Notebook containing them.

| Original lecture cell | Interactive exercise | Learning objective |
| ---: | --- | --- |
| 22 | Fix the grade boundary | Conditional boundaries |
| 35 | Debug the accumulation loop | Loop iteration counts |
| 48 | Find the maximum correctly | Array traversal and initialization |
| 63 | Fix the average function | Numeric types and integer division |
| 72 | Complete the score analyser | Function decomposition and transfer |

The full lecture also contains 22 ordinary teaching programs; the five reference implementations are separate from the Notebook.

[Marker and Metadata specification](docs/NOTEBOOK_CLASSROOM.md) · [Full lecture](examples/CS2310_Score_Analysis.ipynb) · [Separate instructor references](examples/score_analysis_references.json)

## Interactive free Run

The student UI supports persistent execution sessions when the Judge advertises interactive capability. Until the sandbox host passes the additional interactive acceptance, enter the **complete stdin before Run**. This is explicit batch execution, not an interactive terminal. Submit remains batch grading. See [interactive execution](docs/INTERACTIVE_RUN.md).

## Student workflow

Join through the teacher's QR code or link and enter a nickname. **本课堂已发布任务** lists earlier tasks and follows new publications when set to the latest task. Earlier tasks are read-only and retain their own drafts and submission history. **已加入的课堂** lists classrooms joined on this browser and site. Use it to switch rooms without signing up again while the local session is valid.

- **运行代码 (Run):** With a validated native Judge, with an interactive-capable worker, Run keeps one process alive; otherwise enter complete stdin before batch Run.
- **提交代码 (Submit):** Save a formal attempt, independently of Run. Use Ctrl+Enter or Command+Enter as a shortcut. A receipt does not imply a grade. Public test details and hidden test statuses are displayed when results exist.
- **恢复起始代码 / 下载 .cpp:** Restore the original starter after confirmation, or download the current source. The browser retains the current task draft and displays the newest 50 formal attempts for that task.
- **抄送至OPT_CPP:** Open the external OPT CPP visualizer in a new tab with the current source. Provide input, run and inspect results in OPT CPP itself. ClassLab does not import its runtime output as a grade.

For long source code, the external handoff offers a blank visualizer link and manual copy controls. The external site can read the transmitted source and any input you provide there; avoid sending sensitive information.

[Detailed student controls and external-tool privacy](docs/COURSE_DELIVERY.md#student-workflow)

## Architecture

~~~text
Teacher browser                         Student browsers
Notebook parser / exercise editor       C++ editor / Run / Submit
                   \                       /
                    HTTP classroom API
                            |
                   C++20 ClassLab server
             Classroom records / queue / analytics
                            |
                     Private Unix socket
                    Isolated Judge
                (validated host required)
~~~

| Path | Responsibility |
| --- | --- |
| `web/` | Teacher and student interfaces, Notebook parsing, QR generation and code comparison |
| `src/` | C++20 HTTP server, classroom permissions, persistence, submission queue and Judge client |
| `judge/` | Independent C++20 execution worker with deployment isolation checks |
| `examples/` | Original teaching Notebook, separate sample references and legacy examples |
| `tests/` | CTest, protocol checks, trusted C++ fixtures and Playwright browser regression |
| `docs/` | Deployment, classroom usage and development review |

The server uses cpp-httplib and nlohmann/json. Classroom progress refreshes every two seconds; hidden tests are filtered from student-facing task and result details. The browser holds its own role-specific access key and drafts.

## Testing and evidence

From the repository root after building:

~~~bash
ctest --test-dir build --output-on-failure
~~~

Earlier baseline tests passed; the branch-specific checks must be run again after the removal of replay. The teaching lecture test still compiles real C++ examples and validates the authored expected results.

[Historical Notebook integration acceptance](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/actions/runs/45361246934) · [Subsequent UI regression acceptance](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/actions/runs/45364191659) · [Notebook integration PR #16](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/16) · [All workflows](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/actions)

For local browser acceptance, install Playwright, Chromium, Pillow and zxing-cpp and follow the [rehearsal guide](docs/COURSEWORK_DEMO.md).

To verify consecutive publication, start Normal Mode on port 8080 and run:

~~~bash
python3 tests/browser_notebook_publish.py http://127.0.0.1:8080
~~~

The [Notebook classroom workflow](.github/workflows/notebook-classroom.yml) also runs this check in GitHub Actions.

**Verification boundary:** trusted lecture compilation and mock-Judge browser tests do not establish that arbitrary student programs can safely run on a particular host. Full production isolation acceptance is still required.

## Native Judge deployment and current limitations

This branch defaults to submission collection without a Judge. For real C++20 execution, follow the [Judge deployment and security acceptance guide](docs/PHASE_4.md) on a suitable dedicated Linux host. Only after acceptance, configure the Web server to connect to the running Judge:

~~~bash
CLASSLAB_HOST=127.0.0.1 CLASSLAB_PORT=8080 \
  CLASSLAB_JUDGE_SOCKET=/run/classlab-judge/judge.sock ./build/classlab
~~~

The example assumes the approved worker is already running at that socket path. For the complete administrator procedure, including persistent data, service accounts and authenticated school access, see [Running ClassLab](docs/RUN_CLASSLAB.md). Do not bypass the sandbox checks or run arbitrary submissions directly on the Web host. A Codespace with Docker installed is not automatically a valid Judge host.

| Environment variable | Default | Purpose |
| --- | --- | --- |
| CLASSLAB_HOST | 127.0.0.1 | Web listen address |
| CLASSLAB_PORT | 8080 | Web listen port |
| CLASSLAB_DATA | data/classrooms.json | Normal classroom store; one server per file |
| CLASSLAB_JUDGE_SOCKET | empty | Path to an accepted local execution service |

ClassLab is a coursework prototype for small, trusted classrooms, not a public production SaaS platform. Nicknames are not verified accounts; browser access keys must be retained. The server has no account recovery, multi-process storage or public deployment protection. Public deployment and long-term operations are outside the coursework scope.

## Team Contributions

The table records CS2310 team accounts and the work traceable to their original commits and pull requests.

| Team Member | GitHub | Actual Contribution |
| --- | --- | --- |
| Thomas | [ThomasChoi2026](https://github.com/ThomasChoi2026) | Developed the classroom MVP and the Notebook lesson preparation workflow. Defined the requirements and prompts for classroom analysis and student code comparison. |
| aries36white | [aries36white](https://github.com/aries36white) | Linked the student editor to the external OPT CPP tab. [PR #3](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/3) |
| superlulu77 | [superlulu77](https://github.com/superlulu77) | Added starter-code reset, C++ download, and timestamped submission receipts. [PR #1](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/1) |
| godferywong098kirito-blip | [godferywong098kirito-blip](https://github.com/godferywong098kirito-blip) | Added student submission history. [PR #2](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/2) |
| Mizunonamae | [Mizunonamae](https://github.com/Mizunonamae) | Added teacher classroom controls, student removal and praise, and a macOS build fix. [PR #4](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/4) |
| isferr | [isferr](https://github.com/isferr) | Added the weekly timetable and overlap detection. [PR #5](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/5) |

See the [classroom MVP commit](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/commit/4fb68b0921305a08e3cad88a62193acf9f17237e) and [Notebook lesson preparation commit](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/commit/a7dda8450da2b95796ecc2d80550e4aaa537a7d5) for development records.

## Development and further documentation

The latest verified source is maintained on main. New work uses feature branches, automated tests and pull requests. Merge commits preserve original team authors and history.

- [Running ClassLab: isolated Judge and school-server setup](docs/RUN_CLASSLAB.md)
- [Course delivery and architecture review](docs/COURSE_DELIVERY.md)
- [Notebook integration specification](docs/NOTEBOOK_CLASSROOM.md)
- [Coursework demonstration guide](docs/COURSEWORK_DEMO.md)
- [Native Judge acceptance requirements](docs/PHASE_4.md)
- [Project context and handoff](docs/PROJECT_CONTEXT.md)
- [Complete main commit history](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/commits/main/)

## Acknowledgements and third-party tools

We thank our CS2310 instructor, **Professor Chung Chan**, for developing **OPT CPP** [1], the external C++ visualizer that ClassLab links to for student practice. OPT CPP runs C++ programs and shows execution steps, stack frames, variables and heap state. It is published under the DIVE4DEC GitHub account.

OPT CPP builds on the visualization work of **Philip J. Guo**, who created **Python Tutor**, originally **Online Python Tutor** [2–5]. The ClassLab team develops the classroom workflow, editor handoff, submission history, teacher analytics and Judge integration. ClassLab is an independent project. This attribution does not imply participation, sponsorship or endorsement.

| Component | Use in ClassLab | Source and licensing scope |
| --- | --- | --- |
| OPT CPP and Python Tutor | External reference and browser link to OPT CPP | ClassLab ships no visualizer source or WASM assets. The link does not establish the external site's privacy or usage terms. |
| qrcode-generator 1.4.4 | Bundled JavaScript for join QR codes | MIT. The notice is included in [web/vendor/qrcode.LICENSE](web/vendor/qrcode.LICENSE). |
| cpp-httplib v0.28.0 and nlohmann/json v3.12.0 | Build-time dependencies fetched by CMake at pinned versions | MIT. See the source notices for [cpp-httplib](https://github.com/yhirose/cpp-httplib/tree/v0.28.0) and [nlohmann/json](https://github.com/nlohmann/json/tree/v3.12.0). |

### References

1. Chan, C. [OPT_CPP source, runtime documentation and references](https://github.com/dive4dec/OPT_CPP). See the [initial OPT_CPP commit](https://github.com/dive4dec/OPT_CPP/commit/f8b60a93e15139831546a4e4d7c37a39fe217354) for the author credit.
2. Python Tutor. [Official website](https://pythontutor.com/).
3. Python Tutor. [Official C++ Visualizer](https://pythontutor.com/cpp.html).
4. Python Tutor. [Official link integration guide](https://pythontutor.com/for-ai-assistants.html).
5. Guo, P. J. (2013). Online Python Tutor: Embeddable Web-Based Program Visualization for CS Education. *Proceedings of the 44th ACM Technical Symposium on Computer Science Education (SIGCSE '13)*, 579–584. [https://doi.org/10.1145/2445196.2445368](https://doi.org/10.1145/2445196.2445368).
