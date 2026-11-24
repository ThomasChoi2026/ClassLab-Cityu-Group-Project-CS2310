# ClassLab

**Turn C++ lecture notebooks into interactive classroom exercises.**

City University of Hong Kong · CS2310 Computer Programming · Agentic Coding Group Project

ClassLab connects a teacher's existing Jupyter Notebook to a live classroom. Teachers select exercises, publish starter code and tests, and share a QR code. Students edit and submit C++ in their browsers. The teacher can then inspect common code changes, test failures and class participation to decide what to explain next.

The project's distinctive contribution is this **Notebook → exercise → student submissions → classroom feedback** workflow. It complements existing C++ visualizers and automated judges rather than recreating them.

[Quick Start](#quick-start) · [Classroom Demo](#one-minute-classroom-demo) · [Teacher Guide](#teacher-workflow) · [Student Guide](#student-workflow) · [Testing](#testing-and-evidence) · [Team](#team-contributions)

## Quick Start

**Same repository, same application, two startup modes.** No separate website, branch or Docker installation is needed to try the classroom workflow.

| Choose | Command after building | Browser / Codespaces port |
| --- | --- | --- |
| Normal Mode（正式版） | `CLASSLAB_DEMO=0 CLASSLAB_HOST=127.0.0.1 CLASSLAB_PORT=8080 CLASSLAB_JUDGE_SOCKET= ./build/classlab` | 8080 |
| Demo Mode（作业演示） | `python3 demo/run.py --port 8082` | 8082 |

For the coursework presentation, use Demo Mode with the [supplied 74-cell Notebook](examples/CS2310_Score_Analysis.ipynb). For actual classroom records, use Normal Mode. To enable real C++ execution, see [the school-server setup guide](docs/RUN_CLASSLAB.md).

### 1. Build once

Use Linux, WSL or a Linux GitHub Codespace. Requirements: Git, CMake 3.24+, a C++20 compiler (such as GCC), and Python 3. Node.js is needed for the complete test suite. The first build requires internet access to fetch pinned dependencies. No separate frontend build is required.

For a fresh checkout:

~~~bash
git clone --branch main https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310.git
cd ClassLab-Cityu-Group-Project-CS2310
~~~

If you already have the repository open in Codespaces, use its terminal in the repository root instead of cloning it again. Ensure the checkout contains the latest desired main revision before building; preserve any uncommitted work.

~~~bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
~~~

### 2. Choose a mode

#### A. Normal Mode — 正式课堂模式 (port 8080)

~~~bash
CLASSLAB_DEMO=0 CLASSLAB_HOST=127.0.0.1 CLASSLAB_PORT=8080 CLASSLAB_JUDGE_SOCKET= ./build/classlab
~~~

Open **http://127.0.0.1:8080** on the same machine, or use the private Codespaces preview for port **8080**.

Create a classroom, import a Notebook or paste any C++ starter code, and collect actual student submissions. Classroom data persists in `data/classrooms.json` by default.

**The command above deliberately launches without a Judge.** Code submission, class progress and source comparison still work. Native Run and automatic grading require a separately installed and security-accepted Judge (see [Judge deployment](docs/PHASE_4.md)). The external OPT CPP link remains available.

#### B. Demo Mode — 作业演示模式 (port 8082)

~~~bash
python3 demo/run.py --port 8082
~~~

Open **http://127.0.0.1:8082** on the same machine, or use the private Codespaces preview for port **8082**.

A yellow banner identifies Demo Mode. It supports the full classroom workflow and **clearly labelled prerecorded results** for the supplied teaching exercises. It does not compile or execute arbitrary student source code. Classroom data is temporary and is removed on normal shutdown.

For a one-command build, test and Demo launch from a fresh checkout, use `bash demo/start_coursework.sh 8082` instead.

### 3. Open the correct page in Codespaces

1. On GitHub, open the repository's **main** branch and choose **Code → Codespaces**.
2. Build and launch the desired mode in the Codespace terminal using the commands above.
3. Open the **Ports** panel. Forward **8080** for Normal Mode or **8082** for Demo Mode, keep the port **Private**, and click **Open in Browser**.
4. The forwarded HTTPS URL opens the teacher page. Students use its generated join link or QR code. Other devices need a GitHub account authorized to access that private preview.

The two modes can run simultaneously in separate terminals on these ports. Stop either with **Ctrl+C** in its terminal. Do not expose the Judge socket or the Demo service publicly. If a forwarded page cannot open, run `curl -fsS http://127.0.0.1:8080/api/health` (or use port 8082) in another terminal. A normal server returns a ready status; Demo also returns `"demo":true`. Check the startup terminal and port forwarding if the request fails.

### Normal Mode vs. Demo Mode

| Capability | Normal Mode (8080) | Demo Mode (8082) |
| --- | --- | --- |
| Classroom creation, QR join, Notebook import | Yes | Yes |
| Code editing, submissions, classroom analytics | Real classroom records | Real classroom records |
| Native Run and automatic grading | Requires a validated Judge | Prerecorded fixture results only |
| Arbitrary C++20 execution | Only with a validated Judge | No |
| External OPT CPP handoff | Yes | Yes |
| Server-side classroom data | Persistent | Temporary |
| Yellow Demo banner | No | Yes |

## One-minute classroom demo

**Use Demo Mode for a reliable coursework presentation without configuring a native Judge.**

Download the full original teaching Notebook: [CS2310_Score_Analysis.ipynb](examples/CS2310_Score_Analysis.ipynb), also available via the Demo teacher banner's single **下载教学 Notebook（74 Cells / 5 题）** link. On GitHub, click **Download raw file** and save it to the teacher's computer.

1. Create a classroom and switch to **课前备课 (Lesson Preparation)**.
2. Upload the downloaded Notebook directly. ClassLab identifies **5 exercises among 74 cells**. Select **Fix the grade boundary — Cell 22**.
3. Review the automatically populated title, description and starter code; expand **测试用例与易错点** if needed to inspect five test cases (three public, two hidden) and the teacher-only pitfall. Click **发布为当前任务 (Publish)**.
4. Open the student join link in separate browser sessions. Click **演示 Run（回放）**, enter the public input `60`, then click again. The starter produces the prerecorded output `FAIL`. Replace only `score > 60` with `score >= 60`; the same input now produces the prerecorded output `PASS`.
5. Have one student submit the starter and two submit the exact corrected code. The teacher dashboard shows **3 submitted, 2 accepted, 1 failed**. Open the shared code change, explain the boundary error, and choose the next exercise without re-uploading the Notebook.

In a single-minute presentation, prepare the browser sessions and example submissions in advance. The interaction and stored submission records are real; the Demo verdicts are not live C++ execution.

[Detailed rehearsal guide and 60-second English script](docs/COURSEWORK_DEMO.md) · [Verified browser screenshots](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/actions/runs/45361246934/artifacts/14903579794) (GitHub access and artifact retention apply)

## Teacher workflow

| Stage | What the teacher does |
| --- | --- |
| Prepare | Choose **快速课堂 (Quick Classroom)** to paste C++, or **课前备课 (Lesson Preparation)** to import a Notebook and manage locally saved exercises. |
| Configure | Set a title, optional description, starter code, up to 12 public/hidden tests and up to 8 anticipated pitfalls. Explicitly select the blank-start option for independent coding tasks. |
| Publish | Review the editor and publish explicitly; importing or selecting a Notebook cell does not publish a task. |
| Share | Invite students using the join link or QR code; switch to classroom projection for a simplified class display. |
| Review | Inspect each student's latest submission, source diff, test outcomes, shared edits and pitfall evidence. Use them as review clues, not proof of a student's reasoning. |
| Continue | Publish the next exercise without re-uploading. The Notebook stays available in the current page, while the editor clears and the dashboard switches to the active task. Reloading or closing the page requires re-importing the Notebook. |

Additional teacher controls include praise, student removal and a weekly timetable with overlap detection. The lesson library saves drafts in the current browser; it is independent of server-side classroom records.

### Notebook classroom integration

Add a marker as the first nonblank line of a C++ Code Cell (or the first nonblank line after a bare `%%cpp`):

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

The shorter `// @classlab exercise` also works and uses the original cell number as the default title. Optional `metadata.classlab` supplies the task description, tests and anticipated pitfalls. Without markers, the ordinary Notebook browser remains available, including search, filtering, previews and multi-cell code assembly.

The Notebook is parsed locally in the teacher browser (Notebook v4, up to 2 MiB). Ordinary cells are previewed before insertion; marked exercises load their preset fields. Draft replacement requires confirmation when necessary. The teacher must publish explicitly; the app blocks an unintended empty starter or uninserted code combination. Advanced combination, test settings and the lesson library are collapsed by default. Mark teacher reference cells with `// @classlab answer` or Metadata role `answer` / `reference` so the import controls cannot insert them into a student task. Keep private answers and hidden inputs out of the public description and starter code; do not distribute a teacher Notebook containing them.

| Original lecture cell | Interactive exercise | Learning objective |
| ---: | --- | --- |
| 22 | Fix the grade boundary | Conditional boundaries |
| 35 | Debug the accumulation loop | Loop iteration counts |
| 48 | Find the maximum correctly | Array traversal and initialization |
| 63 | Fix the average function | Numeric types and integer division |
| 72 | Complete the score analyser | Function decomposition and transfer |

All five support exact-source Demo playback. The full lecture also contains 22 ordinary teaching programs; the five reference implementations are separate from the Notebook.

[Marker and Metadata specification](docs/NOTEBOOK_CLASSROOM.md) · [Full lecture](examples/CS2310_Score_Analysis.ipynb) · [Separate instructor references](examples/score_analysis_references.json)

## Student workflow

Join through the teacher's QR code or link, enter a nickname, and work on the current exercise in the browser.

- **运行代码 (Run):** With a validated native Judge, the first execution probes stdin consumption. If input is needed, provide the complete input and run again from the beginning; it is not a live interactive terminal. In Demo Mode, only exact registered source and inputs have prerecorded results. New marked exercises accept only public fixture inputs for free Run.
- **提交代码 (Submit):** Save a formal attempt, independently of Run. Use Ctrl+Enter or Command+Enter as a shortcut. A receipt does not imply a grade. Public test details and hidden test statuses are displayed when results exist.
- **恢复起始代码 / 下载 .cpp:** Restore the original starter after confirmation, or download the current source. The browser retains the current task draft and displays the newest 50 formal attempts for that task.
- **抄送至OPT_CPP:** Open the external OPT CPP visualizer in a new tab with the current source and optional external stdin. It remains a separate tool; ClassLab does not import its runtime output as a grade.

For long source code, the external handoff offers a blank visualizer link and manual copy controls. The external site can read the transmitted source and input; avoid sending sensitive information.

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
                     /                  \
        Normal: isolated Judge       Demo: fixed fixtures
        (validated host required)   (no arbitrary execution)
~~~

| Path | Responsibility |
| --- | --- |
| `web/` | Teacher and student interfaces, Notebook parsing, QR generation and code comparison |
| `src/` | C++20 HTTP server, classroom permissions, persistence, submission queue and Judge client |
| `judge/` | Independent C++20 execution worker with deployment isolation checks |
| `demo/` | Explicitly labelled fixed-result classroom rehearsal with temporary storage |
| `examples/` | Original teaching Notebook, separate sample references and legacy examples |
| `tests/` | CTest, protocol checks, trusted C++ fixtures and Playwright browser regression |
| `docs/` | Deployment, classroom usage and development review |

The server uses cpp-httplib and nlohmann/json. Classroom progress refreshes every two seconds; hidden tests are filtered from student-facing task and result details. The browser holds its own role-specific access key and drafts.

## Testing and evidence

From the repository root after building:

~~~bash
ctest --test-dir build --output-on-failure
~~~

The Notebook classroom acceptance workflow at commit `0eb71c2` passed **11/11 CTest tests** with Node.js installed, plus five Chromium browser checks. This includes the 135-cell marker parser, draft protection, private test visibility, original OPT CPP handoff, student history, teacher workflow and full marked-Notebook classroom rehearsal. The lecture test actually compiled and ran 27 code cells and five reference implementations, and verified the 23 exercise cases against both source variants and Demo fixtures.

[Notebook integration acceptance](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/actions/runs/45361246934) · [Subsequent UI regression acceptance](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/actions/runs/45364191659) · [Notebook integration PR #16](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/16) · [All workflows](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/actions)

For local browser acceptance, install Playwright, Chromium, Pillow and zxing-cpp and follow the [rehearsal guide](docs/COURSEWORK_DEMO.md).

To verify consecutive publication, start Normal Mode on port 8080 and run:

~~~bash
python3 tests/browser_notebook_publish.py http://127.0.0.1:8080
~~~

The [Notebook classroom workflow](.github/workflows/notebook-classroom.yml) also runs this check in GitHub Actions.

**Verification boundary:** trusted lecture compilation and mock-Judge browser tests do not establish that arbitrary student programs can safely run on a particular host. Full production isolation acceptance is still required.

## Native Judge deployment and current limitations

Normal Mode defaults to submission collection without a Judge. For real C++20 execution, follow the [Judge deployment and security acceptance guide](docs/PHASE_4.md) on a suitable dedicated Linux host. Only after acceptance, configure the Web server to connect to the running Judge:

~~~bash
CLASSLAB_DEMO=0 CLASSLAB_HOST=127.0.0.1 CLASSLAB_PORT=8080 \
  CLASSLAB_JUDGE_SOCKET=/run/classlab-judge/judge.sock ./build/classlab
~~~

The example assumes the approved worker is already running at that socket path. For the complete administrator procedure, including persistent data, service accounts and authenticated school access, see [Running ClassLab](docs/RUN_CLASSLAB.md). Do not bypass the sandbox checks or run arbitrary submissions directly on the Web host. A Codespace with Docker installed is not automatically a valid Judge host.

| Environment variable | Default | Purpose |
| --- | --- | --- |
| CLASSLAB_HOST | 127.0.0.1 | Web listen address |
| CLASSLAB_PORT | 8080 | Web listen port |
| CLASSLAB_DATA | data/classrooms.json | Normal classroom store; one server per file |
| CLASSLAB_JUDGE_SOCKET | empty | Path to an accepted local execution service |
| CLASSLAB_DEMO | unset | Managed by the Demo launcher; do not manually enable replay in Normal Mode |

ClassLab is a coursework prototype for small, trusted classrooms, not a public production SaaS platform. Nicknames are not verified accounts; browser access keys must be retained. The server has no account recovery, multi-process storage or public deployment protection. Demo replay recognizes only registered source variants and inputs: a different correct solution may have no corresponding fixture. Public deployment and long-term operations are outside the coursework scope.

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

- [Running ClassLab: Normal, Demo and school-server setup](docs/RUN_CLASSLAB.md)
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
