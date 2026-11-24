# ClassLab

**Turn C++ lecture notebooks into interactive classrooms.**

City University of Hong Kong · CS2310 Computer Programming · Agentic Coding Group Project · 2026

[Quick evaluation](#quick-evaluation-and-coursework-testing) · [Official deployment](#official-classroom-use-and-secure-deployment) · [Teacher guide](#teacher-user-guide) · [Student guide](#student-user-guide) · [Design your own notebook](#design-your-own-teaching-notebook) · [Team](#team-contributions)

## Why ClassLab?

Jupyter Notebooks help instructors explain programming concepts, demonstrate code and organise lecture materials. However, when students start working independently, it can be difficult to see how the entire class is progressing, which changes students are making, and which concepts need further explanation. A notebook may contain hundreds of cells, while only a few are intended as interactive exercises. Finding those examples, distributing code and collecting individual responses can interrupt the lesson.

ClassLab connects existing C++ teaching materials to live classroom activities. Teachers select exercises from a notebook, publish starter code and instructions, and invite students through a link or QR code. Students edit and submit C++ in a browser. Teachers then review participation, source differences, shared code changes and available assessment results before moving on to the next concept.

**Teaching materials → Classroom exercise → Student practice → Classroom feedback → Targeted explanation → Next exercise**

The project's distinctive contribution is this continuous teaching feedback loop, rather than another standalone online compiler. ClassLab complements existing code visualisation and assessment tools without requiring teachers to abandon their notebook-based teaching workflow. Its analysis is based on observable submissions and test evidence, not AI inference of students' reasoning.

## Choose the right version

For reviewers who want to experience real program execution as well as the classroom workflow, we recommend the **trusted-native experiment in a suitable private test environment**. For actual teaching deployment, use **`main`**, the official security-oriented implementation.

If you do not have a suitable private environment for the experiment, use `main` without a Judge to explore the classroom workflow safely. Both versions share the teacher and student workflows described below.

| | Quick evaluation and testing | Official classroom deployment |
| --- | --- | --- |
| Branch | [`fix/native-interactive-stdin`](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/tree/fix/native-interactive-stdin) | [`main`](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/tree/main) |
| Intended use | Private coursework demonstration and development testing | Controlled classroom use and school-managed deployment |
| Notebook, classroom, submissions and analytics | Available | Available |
| Real C++ execution | Local GCC, restricted to reviewed source | Independent Judge after deployment acceptance |
| Interactive stdin | For approved source | Requires additional interactive acceptance |
| Per-program isolation | **No sandbox** | Isolated execution architecture; actual-host acceptance required |
| Arbitrary student programs | Not allowed | Only on an accepted execution host |
| Port used in this guide | 8083 | 8080 |

Neither version is a prerecorded demonstration. The classroom activities are real; execution and assessment are available only within each version's stated limits.

## Quick evaluation and coursework testing

[**Open the experimental branch**](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/tree/fix/native-interactive-stdin)

The experiment uses actual GCC compilation, program output, interactive stdin and assessment of reviewed examples without requiring the full Docker/gVisor Judge setup. It is intended for a controlled evaluation of the product, not an open student execution service.

> **Safety requirement:** This experiment has no independent program sandbox. Use it only in a private, non-root Linux test environment where the execution process cannot access sensitive files, credentials or unrelated workloads. Use reviewed source and trusted, bounded inputs only. Do not expose the service publicly or approve unreviewed student code. If these conditions cannot be met, use the official submission-only version instead.

### 1. Build the experiment

Requirements: Linux, WSL or a suitable Linux GitHub Codespace; Git; CMake 3.24+; a GCC compiler supporting C++20; Python 3; and Node.js for the full test suite. The initial build downloads pinned dependencies and requires internet access. No separate frontend build or Jupyter installation is needed to import the sample notebook.

```bash
git clone --branch fix/native-interactive-stdin https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310.git classlab-native
cd classlab-native
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
```

If you already have a Codespace on this branch, run the two CMake commands from its repository root instead of cloning again.

### 2. Start the reviewed-source runner

```bash
python3 judge/trusted_native.py --trusted-local-only --port 8083
```

Open http://127.0.0.1:8083 on the same machine. In Codespaces, follow [the private preview instructions](#opening-classlab-in-github-codespaces) using port 8083.

The launcher starts the classroom service and the reviewed-source GCC worker. It loads eligible source from the supplied demonstration notebook and reference implementations at startup. Source eligibility is based on matching reviewed source text (with surrounding whitespace normalised), not on whether a submission is logically correct. Do not modify unrelated formatting or remove the marker when reproducing an approved example. Unapproved source can be submitted and recorded, but will not be compiled or graded by this experiment. Basic resource limits are not a substitute for sandboxing.

### 3. Try a complete classroom activity

[**Download the AI-generated demonstration notebook**](examples/CS2310_Score_Analysis.ipynb) — open the GitHub file and select **Download raw file**. It contains 74 cells, including five marked interactive exercises. This is synthetic AI-generated teaching material prepared to demonstrate ClassLab, not an official course handout or an independently authored textbook.

1. Open the teacher page, enter a class name and click **Create classroom**.
2. In **Lesson Preparation**, import the downloaded `.ipynb` file. Confirm that ClassLab detects five interactive exercises among 74 cells.
3. Select **Fix the grade boundary — Cell 22**. Review the title, description, starter code and preset tests, then click **Publish as current task**.
4. Copy the classroom join link. Open it in a separate browser profile or private window with authorised access to the preview, enter a display name and click **Join Classroom**.
5. In the student editor, keep the supplied starter unchanged. Click **Run code**, enter `60`, and click **Send input** when available. The actual program output is `FAIL`. Submit the starter to record an attempt.
6. Replace only `score > 60` with `score >= 60`, retaining the rest of the approved source. Alternatively, copy the exact `referenceSource` for **Fix the grade boundary** from the [demo references](examples/score_analysis_references.json) (decode the JSON string as C++ text, not literal JSON escapes). Run with `60` again; the actual output is `PASS`. Click **Submit code**.
7. Return to the teacher dashboard. Review the submission and its changes from the starter. To compare different students, join from additional independent browser profiles and submit the original and corrected versions separately.
8. Select and publish the next marked exercise without re-importing the notebook.

The reference file is public demonstration material. Real private teaching answers must not be published in a public repository.

### 4. Stop the experiment

Press `Ctrl+C` in the launch terminal. The experimental classroom store is separate from the official store: `data/trusted-native-classrooms.json`.

[Experiment documentation](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/blob/fix/native-interactive-stdin/docs/RUN_CLASSLAB.md)

## Official classroom use and secure deployment

[**Open the official `main` branch**](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/tree/main)

The official application separates the classroom web service from the execution worker. It does not compile or execute arbitrary student programs directly on the web host, fall back to the trusted-native runner, or replay prerecorded results. The independent Judge must pass deployment acceptance before native execution and assessment are enabled.

### 1. Build and use the classroom without a Judge

Requirements: Linux, WSL or Linux GitHub Codespaces; Git; CMake 3.24+; a C++20 compiler; Python 3; and Node.js for the full test suite. Internet access is needed for the initial dependency download.

```bash
git clone --branch main https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310.git
cd ClassLab-Cityu-Group-Project-CS2310
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
```

Start the official classroom server without connecting a Judge:

```bash
CLASSLAB_HOST=127.0.0.1 \
CLASSLAB_PORT=8080 \
CLASSLAB_JUDGE_SOCKET= \
./build/classlab
```

Open http://127.0.0.1:8080, or use the private Codespaces preview for port 8080. Notebook preparation, classroom creation, QR joining, task publication, real student submissions, source comparison, history, CSV export and the external OPT CPP handoff remain available. Native Run and automatic assessment are unavailable; submitted work is recorded without a grade.

### 2. Environment requirements for real student-code execution

For full deployment, a school or system administrator must provide an approved environment and complete the documented actual-host acceptance checks.

| Component | Requirement |
| --- | --- |
| Execution host | Dedicated Linux x86-64 host or suitable dedicated VM, without unrelated sensitive workloads |
| Container engine | Local Docker daemon |
| Isolation runtime | gVisor `runsc` recommended; any documented alternative requires its own acceptance on a dedicated VM |
| Resource control | Effective cgroup v2 CPU, memory and PID limits |
| Compiler | Pinned GCC 14.3.0 image, C++20 |
| Service identities | Separate Judge and web-service users; web service has no Docker daemon access |
| Filesystem and network | Restricted student containers without host-path, credential, classroom-data or Docker-socket mounts; network isolation |
| Communication | Private Unix socket between web service and Judge |
| Acceptance | Validate isolation, limits, timeouts, cleanup and recovery on the intended host; additional checks for interactive execution |

A Codespace or a server with Docker installed does not automatically satisfy these requirements. A suitable school-managed server or VM may be sufficient; a paid commercial server is not inherently required. The software tests in this repository do not certify a production host.

Follow these guides in order:

- [Running ClassLab — administrator setup](docs/RUN_CLASSLAB.md)
- [Judge isolation and deployment acceptance](docs/PHASE_4.md)
- [Interactive Run acceptance](docs/INTERACTIVE_RUN.md), if persistent input sessions are required

### 3. Connect the accepted Judge

After the administrator has completed acceptance, installed and started the approved worker and configured the service accounts and socket permissions, start ClassLab as the intended web-service user:

```bash
CLASSLAB_HOST=127.0.0.1 \
CLASSLAB_PORT=8080 \
CLASSLAB_JUDGE_SOCKET=/run/classlab-judge/judge.sock \
./build/classlab
```

This command assumes the accepted worker is already running at that socket path. It is not a substitute for installing or validating the Judge.

| Accepted capability | Student experience |
| --- | --- |
| Batch Run | Enter all stdin before running; receive the complete result. |
| Interactive Run | Start a persistent program, send input in stages, receive incremental output, send EOF or stop. Requires additional actual-host acceptance. |
| Formal Submit | Independent batch assessment against configured tests when a suitable Judge is available. |

Keep execution disabled if the required checks fail. Do not bypass either acceptance requirement.

### 4. Provide controlled classroom access

Use a school-managed authenticated HTTPS reverse proxy or approved internal access route. Students join via the teacher's link or QR code. Keep the Judge socket and Docker daemon private. The current prototype does not provide production-grade account management or public-service abuse protection. Protect and back up the official classroom store, `data/classrooms.json` by default, and use one server per data file.

## Opening ClassLab in GitHub Codespaces

1. Open the desired GitHub branch and choose **Code → Codespaces**. Create or open a Codespace for that branch.
2. In the repository terminal, confirm the checkout with `git branch --show-current`. Preserve uncommitted work before changing branches.
3. Run the build and startup commands for the chosen version.
4. Open the VS Code **Ports** panel. Forward port 8083 for the experiment or 8080 for the official service.
5. Keep the port **Private** and click **Open in Browser**. The forwarded HTTPS address opens the teacher page.
6. For student testing, use independent browser sessions authorised to access the same private preview. A QR code does not grant access to a private Codespaces port. The local `127.0.0.1` address is not reachable from another device as the teacher's server.
7. Stop the service with `Ctrl+C` in its terminal.

Do not make a preview public just to simplify a demonstration. A public source repository is not a public execution service.

## Key features

| Feature | What ClassLab provides |
| --- | --- |
| Notebook integration | Direct `.ipynb` import, marked exercise recognition, search, filters, preview and optional multi-cell assembly |
| Lesson preparation | Quick Classroom, saved exercises, editable starter code, public/hidden tests and expected pitfalls |
| Live classroom | QR/link joining, explicit publication, consecutive tasks and classroom projection |
| Student workspace | C++ editing, independent Run and Submit, input sessions where supported, result copying, starter reset and `.cpp` download |
| OPT CPP integration | One-click source handoff to the external C++ visualiser |
| Classroom analytics | Participation, submissions, source differences, shared edits, available test outcomes and selected-task CSV export |
| Classroom management | Previous classrooms and tasks, student submission history, removal, praise and weekly schedule overlap detection |

Native Run, grading and interactive stdin depend on the execution environment described above.

## Teacher user guide

The following classroom workflow is shared by both versions. Use the teacher page's **User Guide** for an in-app reminder. Assessment and execution controls depend on the current runner.

### 1. Create a classroom and invite students

- Enter a **Class Name**, for example `CS2310 Lecture`, and click **Create classroom**.
- Find **Classroom Join Link** under the invitation section. Click **Copy Link** to share it, or enlarge the QR code for students to scan.
- Students can join before a task has been published. Confirm that they can access the service address.
- Alternatively, open **Lesson Preparation** on the initial setup page to prepare and save exercises before creating a classroom. Create a classroom before publishing.

### 2. Choose a preparation mode

| Mode | Use |
| --- | --- |
| **Lesson Preparation** | Default after creating a classroom. Import notebooks, select exercises and manage saved drafts. |
| **Quick Classroom** | Paste or type C++ directly for an ad-hoc exercise without importing a notebook. |

The preparation workspaces keep separate drafts. Switch modes without intentionally replacing the other workspace's current draft.

### 3. Import a notebook

1. Download the [AI-generated demonstration notebook](examples/CS2310_Score_Analysis.ipynb), or prepare your own as described in [Design your own teaching notebook](#design-your-own-teaching-notebook).
2. Open **Lesson Preparation** and select the local `.ipynb` file using **Notebook File**.
3. Check the displayed file name, total original cell count, recognised exercise count and any invalid-metadata warnings. The demo should show 74 cells and five exercises.
4. The interactive-exercise filter is selected initially when marked exercises are present; otherwise all cells are shown. Use **Search Cells** and **Filter Type** to find content by cell number or source keyword.

ClassLab parses the notebook in the teacher's browser. The full file, unrelated cells and notebook outputs are not uploaded to the classroom server. Only selected task fields are sent when a task is published.

### 4. Load a marked interactive exercise

Click an exercise such as **Fix the grade boundary — Cell 22**. Its title, starter code and any preset description, tests and pitfalls are loaded together. If loading would replace edited work, confirm only when ready; cancel to retain the existing draft. **Load interactive exercise** can retry the load.

Selecting a marked exercise prepares the task; it does **not** publish it automatically.

### 5. Use ordinary cells and Markdown

For an unmarked C++ cell, click the cell to preview it, then click **Use this cell as starter code**. Confirm that the source appears in **C++ Starter Code (Code Students Will Receive)**. Previewing alone does not insert code.

For an ordinary Markdown cell, use **Append to Task Description** to add its text to the public instructions. Marked teacher-reference cells cannot be inserted through these controls.

### 6. Combine related code cells

1. Select an ordinary C++ cell and expand **Combine cells (advanced)**.
2. Click **Add to selection**, then select and add the other required ordinary code cells.
3. Review the selection and click **Use selected cells as starter code**.
4. Check the assembled source in the starter editor. Assembly follows the notebook's original order, not the order in which cells were clicked.

Resolve missing dependencies, duplicate definitions or multiple `main()` functions before publishing. ClassLab does not automatically compile or repair arbitrary cell combinations. Load marked interactive exercises individually to keep their code and associated tests together. A pending, unapplied selection must be resolved before publication.

### 7. Review the task editor

| Field | Meaning |
| --- | --- |
| **Title** | Required exercise name |
| **Task Description (Optional)** | Public instructions students should read |
| **C++ Starter Code (Code Students Will Receive)** | The actual source delivered to students |

Edit any imported fields as needed. Students receive the final editor contents, not the preview. To intentionally start with an empty editor, select **Let Students Start from a Blank Template**. This explicit choice prevents accidental blank-code tasks.

### 8. Configure test cases

Expand **Test cases and pitfalls**, then click **Add Test Case**. For the grade-boundary exercise, an example configuration is:

| Field | Example |
| --- | --- |
| Name | Boundary |
| Visibility | Public |
| Standard input | `60` |
| Expected output | `PASS` (followed by a newline) |

Add more cases as needed, up to 12 per task. A **Public** test exposes its input and expected output to students; a **Hidden** test does not expose these contents in the student-facing task or result API. Hidden result rows provide an ordinal label and status only. Keep answers out of public instructions and starter code.

Tests are optional. Without a Judge, submissions are still stored, but tests do not produce real verdicts. In the experiment only approved source can be assessed.

### 9. Configure expected pitfalls

Under **Expected Pitfalls (Teacher Only)**, click **Add Pitfall**. For example:

| Field | Example |
| --- | --- |
| Pitfall name | Exclusive instead of inclusive |
| Review notes | Trace the equality case. |
| Source snippet (exact text) | `score > 60` |
| Linked test case number | `1` |

Up to eight pitfalls are supported per task. The source snippet is a literal text match, not a semantic analysis. Link the pitfall to a test by its position if appropriate. ClassLab reports exact text matches and linked test failures separately; either may be absent or differ from the other. A linked failure requires an actual assessment result.

### 10. Save exercises before class

Expand **Lesson Preparation Exercise Library (Optional)**.

| Control | Action |
| --- | --- |
| **Save New Exercise** | Save the current exercise as a local draft. |
| **Load** | Load the selected saved exercise. |
| **Update Loaded Exercise** | Update the currently loaded draft. |
| **Delete Selected Exercise** | Delete the selected saved draft. |

Drafts are stored in the current browser, independently of published tasks and server-side student records. They do not rewrite the imported `.ipynb` file or automatically synchronise to another browser.

### 11. Publish the exercise

Review the title, public description, final starter code, test visibility and pitfalls. Confirm that any intended cell combination has been applied, and no private answer has been placed in a public field. Click **Publish as current task**.

Students following the latest task receive the new exercise automatically. If publication fails, the editor and imported notebook remain available for a retry. Check the feedback message before retrying.

### 12. Inspect individual submissions

Open **Classroom Progress** to see student participation, submission counts, attempts and available assessment statuses. Open a student's latest submission to inspect **Changes from starter code**, then expand **View complete starter code and student code** to read both sources.

The teacher's view is based on formal submissions, not each student's unsent editor changes or private Run activity.

### 13. Review shared classroom problems

| Section | What to review |
| --- | --- |
| **Common code changes** | Source changes shared across student submissions |
| **Common test failures** | Failed cases among assessed submissions |
| **Common compiler diagnostics** | Shared compilation diagnostics when available |
| **Expected pitfalls and submission feedback** | Evidence related to teacher-defined text snippets and linked tests |

For example, several students may change `score > 60` to `score >= 60`. Use this observation to discuss inclusive boundaries. Source comparison works without a Judge; test and compiler evidence require execution results. Do not infer actual understanding or assign a pass/fail grade solely from a code pattern.

### 14. Project the classroom

Click **Classroom Projection** to show a simplified classroom view with the join QR code, current task and submission progress. Switch back to the full dashboard to prepare the next exercise or inspect student submissions.

### 15. Continue to the next exercise

Select the next marked exercise from the same imported notebook, review its fields and publish again. The notebook remains loaded within the current page; the previous task's editor fields are cleared after publication to avoid mixing exercises. Previous published tasks and submissions are retained. Refreshing or closing the page requires re-importing the notebook. Use the exercise library for reusable local drafts.

### 16. Review earlier tasks

In **Classroom Progress**, choose an earlier exercise using **View published tasks**. This changes only the teacher's displayed records, not the active student task. Return to **Latest task** to see the live classroom again. The projection follows the latest task.

### 17. Export classroom results

Click **Export Current Assignment CSV** in **Classroom Progress**. The export contains the currently selected task's student records, including students who have not submitted and actual scores when available. It does not include full source code, access credentials or hidden test contents. It is a selected-task export, not an entire-semester report. Protect exported student data appropriately.

### 18. Manage classrooms, students and schedules

- **Create New Classroom** creates another classroom; **Switch Managed Classrooms** returns to classrooms whose access keys remain in this browser.
- Teacher controls allow praise and student removal. Removal permanently deletes that student's submission history in the classroom; confirm carefully.
- Expand **Weekly Schedule**, enter a course name, day, start and end time, then click **Add Time Slot**. The timetable detects overlapping time slots.

## Student user guide

### 1. Join and read the task

Open the teacher's classroom link or scan the QR code. Enter a **Display Name** and click **Join Classroom**. No separate ClassLab account is required. If no task has been published, wait for the teacher to publish one.

Read the task title, optional description and starter code. Expand **Public Test Cases** to see available example inputs and expected outputs. Edit your answer in **Your C++ Source Code**.

### 2. Run and debug C++

**Interactive Run:** When the worker supports persistent sessions, click **Run code**, enter an input line in the stdin field and click **Send input**. Repeat as needed. Use **End input (EOF)** when no more input should be supplied, and **Stop** to terminate a running program. The same process remains alive across input sends. Run output may arrive incrementally; prompt visibility depends on C++ buffering, so flush prompts when needed.

For example, the following program reads two integers separately:

```cpp
#include <iostream>
int main() {
    int a, b;
    std::cout << "First number: " << std::flush;
    std::cin >> a;
    std::cout << "Second number: " << std::flush;
    std::cin >> b;
    std::cout << a + b << '\n';
}
```

On an accepted interactive worker, send `5` and then `7` to obtain `12`. This illustration is not necessarily on the experiment's approved-source list; use the supplied demo source for experimental execution.

**Batch Run:** If the worker supports only complete-input execution, enter all required input before clicking **Run code**, for example:

```text
5
7
```

Batch Run does not support input sends after execution starts.

**No Judge:** If execution is unavailable, continue editing, use OPT CPP or download the `.cpp` file, and submit to the classroom. A submission can be valid without an automated grade. In the experiment, source not approved for execution is also recorded without grading.

### 3. Use the external OPT CPP visualiser

1. Click **Send to OPT CPP** next to the code editor.
2. The current source is handed off to OPT CPP in a new browser tab.
3. Provide input and run within OPT CPP itself. Use its available step controls to inspect program execution, variables, stack frames and memory state.
4. Return to ClassLab to revise or formally submit your code.

If a long source cannot be transmitted through the generated link, use **Open blank OPT CPP** and **Copy Current Code** to transfer it manually. OPT CPP is an independent external tool: its output does not become a ClassLab assessment result. Avoid sending sensitive source or data.

### 4. Read and copy execution results

Review stdout, stderr, compiler diagnostics, runtime errors and exit information where available. Use **Copy result** in the Run result area to copy output and diagnostics. If clipboard access fails, use the provided selectable fallback. Copying output does not submit an answer.

### 5. Submit formally

Click **Submit code**, or use `Ctrl+Enter` / `Command+Enter` in the editor. The server saves the attempt and displays a timestamped receipt or assessment status.

| Action | Purpose |
| --- | --- |
| Run code | Private practice and debugging; no formal submission |
| Submit code | Save a formal attempt for the teacher, with automatic assessment if available |

A successful Run is not a submitted answer. A queued or ungraded submission is not an accepted verdict. View **Latest Assessment Result** for the latest available assessment, and expand **Submission and Assessment History (Most Recent 50 Attempts)** for the current task's recent attempts.

### 6. Manage code and previous activities

| Control | Action |
| --- | --- |
| **Copy Code** | Copy current source. |
| **Restore Starter Code** | Replace the editor with the teacher's original starter after confirmation. Save any work you want to keep first. |
| **Download .cpp File** | Download current source. |
| **Available Assignments** | View earlier tasks and their retained drafts and history; historical tasks are read-only. Return to the latest task to Run or Submit. |
| **Enrolled Classes** | Switch between classrooms joined in this browser while their access keys remain valid. |

## Design your own teaching notebook

ClassLab is designed to work with existing C++ lecture notebooks. A teacher can keep normal explanations, examples and reference material in the same teaching file, while explicitly marking only the code cells intended for student participation.

**You do not need to mark every code cell, install a ClassLab Jupyter extension or rewrite the entire notebook.** Recognition is based on a documented source marker and optional cell metadata, not AI classification. A recognised exercise can be loaded with its configuration; only the teacher can publish it.

### 1. Organise a lesson around selected activities

For each concept, consider using the following structure:

| Notebook content | How to prepare it | What ClassLab does |
| --- | --- | --- |
| Markdown explanation | Ordinary Markdown cell | Available for preview and manual insertion into public instructions |
| Lecturer's worked example | Ordinary C++ cell, no ClassLab marker | Available for browsing and manual starter-code insertion |
| Student debugging or coding activity | C++ Code cell beginning with `// @classlab exercise: Title` | Recognised in the interactive-exercise list; loads as a task when selected |
| Teacher's reference solution | Separate file, or a reference-marked cell | Reference-marked cells are preview-only in the import controls |
| Next concept | Repeat the sequence | Keep the same notebook loaded and publish the next activity when ready |

For automatic loading, make each marked exercise a self-contained starter program where practical. Include headers, required helper functions, class definitions and a suitable entry point. Place blanks or deliberate bugs in the starter as appropriate. The parser may recognise fragments but warns if it finds no `main()`; it does not resolve dependencies or combine neighbouring cells automatically.

### 2. Add the exercise marker in the correct location

In a Jupyter Notebook v4 **Code** cell, place the case-sensitive marker on the first nonblank line:

```cpp
// @classlab exercise: Fix the grade boundary
#include <iostream>

int main() {
    int score;
    std::cin >> score;
    if (score > 60) std::cout << "PASS\n";
    else std::cout << "FAIL\n";
}
```

This is an ordinary C++ comment, so the marker itself does not affect normal C++ compilation. A title is optional. If the notebook uses a bare `%%cpp` wrapper, put the marker immediately after that wrapper, allowing blank lines:

```cpp
%%cpp
// @classlab exercise: Fix the grade boundary
#include <iostream>
int main() {
    int score;
    std::cin >> score;
    std::cout << (score > 60 ? "PASS" : "FAIL") << '\n';
}
```

The importer removes the bare wrapper for the starter code, preserving the marker and C++ source apart from leading whitespace. The second example illustrates authoring syntax; it is not the exact approved experimental demo source.

| Marker or location | Result |
| --- | --- |
| `// @classlab exercise: Fix the grade boundary` at the beginning of a valid C++ Code cell | Recognised exercise with a custom title |
| `// @classlab exercise` | Recognised exercise with a metadata title, or `ClassLab Exercise · Cell N` |
| `// @classlab exercise;` | Not a valid marker |
| `// @classlab Exercise: Example` | Not a valid marker; case matters |
| `// @classlab exercise:` with no title | Invalid marker; remove the colon or add a title |
| Marker after normal source lines, inside a string or in a Markdown cell | Not a valid exercise marker |
| Metadata without a valid exercise marker | Does not create an exercise; invalid tagged content is blocked |

Do not put a semicolon on the marker. Keep normal C++ semicolons in the program. An explicit marker title takes priority over a metadata title, then the original cell number is used as the fallback.

### 3. Preload instructions, tests and pitfalls (optional)

For a fully prepared lesson, add optional `classlab` configuration to the **same Code cell's metadata**. The source marker is still required. This lets the teacher select one activity during class and load its complete task configuration without re-entering it.

In a notebook editor, open that cell's **Cell Metadata** editor. Add the following object alongside existing metadata keys. If your editor does not expose cell metadata, save a copy of the `.ipynb`, open it as JSON, locate the marked cell in the `cells` array and edit its `metadata` object. Do not add the JSON to the C++ source or to the notebook's top-level metadata.

```json
{
  "classlab": {
    "version": 1,
    "role": "exercise",
    "description": "Read an integer score from 0 to 100. Print PASS for scores >= 60; otherwise print FAIL. Fix the boundary in the starter code.",
    "testCases": [
      {
        "name": "Boundary",
        "input": "60",
        "expectedOutput": "PASS\n",
        "visibility": "public"
      },
      {
        "name": "Below boundary",
        "input": "59",
        "expectedOutput": "FAIL\n",
        "visibility": "public"
      },
      {
        "name": "Zero",
        "input": "0",
        "expectedOutput": "FAIL\n",
        "visibility": "hidden"
      }
    ],
    "pitfalls": [
      {
        "name": "Exclusive instead of inclusive",
        "note": "Trace the equality case.",
        "needle": "score > 60",
        "testNumber": "1"
      }
    ]
  }
}
```

The example is a valid metadata configuration for the marked boundary exercise. It preloads public instructions, three tests (two public and one hidden) and a teacher-only pitfall linked to the first test. It is a shortened authoring example; the supplied demo's Cell 22 contains five tests.

In raw notebook JSON, the relevant structure is `cells[N].metadata.classlab`, where `N` is the zero-based array index. For the demo's original Cell 22, use `cells[21].metadata.classlab`. Preserve the cell's existing `source`, `cell_type`, and other metadata. Do not replace the notebook's outer JSON structure.

| Field | Meaning and constraints |
| --- | --- |
| `version` | Optional; if supplied, integer `1` |
| `role` | Optional `exercise`; `answer` or `reference` reserves content for teacher preview |
| `title` | Optional nonblank fallback title; maximum 53 UTF-16 code units / 160 UTF-8 bytes |
| `description` | Optional public text; maximum 3,000 units / 10,000 bytes |
| `testCases` | Optional array, up to 12; each requires `name`, `input`, `expectedOutput`, `visibility` |
| `visibility` | Exactly `public` or `hidden`; test inputs and outputs must be strings, including when empty |
| `pitfalls` | Optional array, up to eight; each requires `name`, with optional `note`, `needle` and `testNumber` |
| `needle` | Literal source snippet, not a regular expression or AI prompt |
| `testNumber` | String such as `"1"` referring to an existing one-based test position; omit or use an empty string if unlinked |

Preserve test order, or update linked test numbers when reordering. Unknown ClassLab fields, unsupported types, invalid references and oversized values cause validation warnings and block the tagged cell from loading; invalid tagged cells are excluded from the recognised exercise count. The [full metadata specification](docs/NOTEBOOK_CLASSROOM.md) lists field-by-field limits. Do not use `null` in place of optional values.

Metadata is not mandatory. A valid marker plus C++ source is sufficient; descriptions, tests and pitfalls can be added manually in the ClassLab editor after import. Website edits affect the task or saved draft, not the original `.ipynb` on disk.

### 4. Keep teacher answers separate

Prefer a separate private reference file for real lessons. To keep a solution in a teacher-only notebook cell, use either of the following comments at the beginning of a Code cell (after bare `%%cpp`, if present):

```cpp
// @classlab answer
```

```cpp
// @classlab reference
```

Alternatively, set `metadata.classlab.role` to `answer` or `reference` in a Code or Markdown cell. Such cells are preview-only and cannot be loaded, combined or appended to student instructions through the import controls.

This protection applies to the import workflow, not to the underlying file's confidentiality. Do not distribute a notebook containing private answers to students or publish it in a public repository. Hidden tests and pitfalls are teacher-only in the normal classroom interface, but must not be manually pasted into public task fields.

### 5. Save, import and verify before class

1. Save the notebook in Jupyter Notebook v4 `.ipynb` format (up to 2 MiB).
2. Open **Lesson Preparation** and select the file. Confirm that the detected interactive-exercise count matches the activities you marked.
3. Select each marked exercise and check the title, source, instructions, tests and pitfalls. Expand **Test cases and pitfalls** to inspect preset values.
4. Resolve any warnings. If an exercise is missing, check that the marker is in a Code cell, is correctly spelled and is on the first nonblank line (after bare `%%cpp`, if used). Check that metadata is attached to that cell rather than the whole notebook.
5. Check that the starter is complete and that public/hidden test outputs are correct. Use an accepted Judge or appropriate trusted offline tools to validate the exercise before teaching. The experimental runner cannot execute arbitrary new notebook source.
6. Optionally save each exercise in the local lesson library. Publish only when ready for students to receive the task.
7. During class, select each subsequent activity from the same file. The notebook stays available until the page is refreshed or closed.

Unsupported notebook commands, including `%%hermes`, `%%cpp` with arguments, Python and shell directives, must be converted to compatible C++ manually. Source is limited to 20,000 UTF-16 code units / 65,536 UTF-8 bytes for a marked exercise. An ordinary C++ cell remains usable through manual insertion; no marker is required for that workflow.

[Complete Notebook Classroom Integration Guide](docs/NOTEBOOK_CLASSROOM.md)

## AI-generated demonstration teaching material

[**CS2310 — From Control Flow to Procedural Abstraction: score analysis demo**](examples/CS2310_Score_Analysis.ipynb)

The AI-generated demonstration notebook contains 74 cells, 22 ordinary teaching programs and five interactive exercises. It illustrates how explanations, examples, marked activities and preconfigured tests can be organised in a single lesson. It is synthetic demonstration material, not a claim of independently authored teaching content or an official CS2310 lecture.

| Original cell | Interactive activity | Learning objective |
| ---: | --- | --- |
| 22 | Fix the grade boundary | Conditional boundaries |
| 35 | Debug the accumulation loop | Loop iteration counts |
| 48 | Find the maximum correctly | Array traversal and initialisation |
| 63 | Fix the average function | Numeric types and integer division |
| 72 | Complete the score analyser | Function decomposition and transfer |

The [separate demo reference file](examples/score_analysis_references.json) contains reference source and historical fixture data. The current official and experimental versions do not use prerecorded fixture outputs as execution results. The experiment compiles and runs approved source using real GCC. The supplied demo is available for reviewers to inspect, modify for their own teaching materials and test within the relevant version's execution boundary.

[Classroom demonstration guide](docs/COURSEWORK_DEMO.md)

## Troubleshooting

| Problem | What to check |
| --- | --- |
| Which version should I use? | Use the private experiment for reviewed-source evaluation; use `main` for official deployment or submission-only evaluation. |
| Page does not open | Check the launch terminal, correct branch, server address and port. |
| Codespaces preview does not open | Check private port forwarding, browser authentication and preview access. |
| Students cannot join | Verify that the join address is reachable and authorised for their device; localhost is not a shared remote address. |
| No marked exercises appear | Check Code cell type, marker spelling, first-line position, supported directives and cell metadata warnings. |
| Ordinary cell was selected but students received no code | Click the starter-code insertion control; verify the final editor before publishing. |
| A multi-cell selection cannot be published | Apply the selection to the starter editor and check its assembled source. |
| Blank starter cannot be published | Insert source or explicitly choose the blank-editor option. |
| Notebook disappears after reload | Re-import it; use the lesson library for reusable drafts. Publishing alone does not remove the notebook. |
| Previous assignment is missing | Use **View published tasks** (teacher) or **Available Assignments** (student). |
| Run is unavailable | Check Judge connectivity and acceptance. Submissions can still be recorded. |
| Experimental source is rejected | Use the exact reviewed demo source. Do not bypass the approval mechanism. |
| Input cannot be sent in stages | Check whether the worker supports Interactive Run or only Batch Run. |
| Program prompt is not visible | Check buffering; flush output when necessary. |
| Teacher cannot see a student's Run | Run is independent of Submit; the student must formally submit. |
| No grade appears after submission | Check for pending assessment, absent tests, unavailable Judge or unapproved source. An ungraded attempt is not a failure or a pass. |
| OPT CPP cannot receive a long source | Use the manual copy and blank-page fallback. |
| Previous classroom is inaccessible | Check whether the browser's classroom access key is still available. |
| CSV lacks scores | Unassessed attempts have no invented scores. |

From another terminal on the server host, check the official service:

```bash
curl -fsS http://127.0.0.1:8080/api/health
```

For the experiment as launched in this guide, use port 8083. See [Running ClassLab](docs/RUN_CLASSLAB.md) for further deployment details.

## System architecture

```text
Teacher browser                   Student browsers
Notebook parser / task editor     C++ editor / Run / Submit
                  \                /
                   HTTP classroom API
                           |
                    C++20 web server
              Records / queue / analytics
                           |
                    Private Unix socket
                           |
                 Accepted isolated Judge
                 Interactive / batch
```

The official server handles role-specific access, classroom state, persistence, task publication, submissions and analytics. The isolated Judge handles execution and communicates with the server through a private socket. The experimental branch instead connects a restricted reviewed-source local GCC worker; it has no independent program sandbox.

| Directory | Responsibility |
| --- | --- |
| `web/` | Teacher and student interfaces, notebook parser, QR codes and source comparison |
| `src/` | C++20 server, permissions, classroom records and Judge communication |
| `judge/` | Independent execution worker and deployment checks (official branch) |
| `examples/` | AI-generated demonstration teaching material and reference examples |
| `tests/` | CTest, protocol checks, trusted C++ fixtures and Playwright browser acceptance |
| `docs/` | Usage, notebook authoring, deployment and development documentation |

Technology: C++20, HTML, CSS, JavaScript, Python, cpp-httplib, nlohmann/json, and Docker/gVisor for the official isolation architecture.

## Testing and evidence

After building either branch, run:

```bash
ctest --test-dir build --output-on-failure
```

The automated checks cover notebook parsing and filtering, draft protection, consecutive publication, accurate starter-code delivery, public/hidden test separation, submission history, classroom records, shared source changes, CSV export, Run-result copying and OPT CPP handoff. The experiment additionally tests reviewed-source real GCC execution and persistent stdin. Trusted fixtures and mock-worker browser tests do not establish the safety of arbitrary student execution on an actual production host.

| Version | Tested revision | Recorded result |
| --- | --- | --- |
| Official `main` | `42c75b8` | [10/10 CTest and Chromium classroom regression passed](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/actions/runs/45408883975) |
| Trusted-native experiment | `36c5c0e` | [12/12 CTest, reviewed-source GCC and browser regression passed](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/actions/runs/45408846452) |

[All GitHub Actions results](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/actions)

These links identify specific tested revisions, not a blanket claim about every future commit. Production-host isolation and interactive acceptance remain separate requirements.

## Current limitations and privacy

ClassLab is a coursework prototype intended for small, controlled classrooms, not a production-certified public service.

- Official execution is disabled without an accepted Judge. The experimental worker is restricted to reviewed source and must remain private.
- Nicknames and browser-held access keys are not verified school accounts. Protect access keys, classroom data and exported CSV files.
- The imported notebook is parsed locally; publishing sends the selected task configuration. Protect private notebook files and reference answers independently of the interface.
- OPT CPP is an external tool that can read transmitted source and any input supplied there. Do not send confidential information.
- Classroom analysis provides observable evidence and review clues, not proof of a student's reasoning or understanding.
- The public availability of source code does not imply that a running classroom service, experimental worker or Judge socket should be publicly accessible.

## Team contributions

ClassLab was developed collaboratively by six CS2310 group members. Their contributions are documented below using GitHub accounts and traceable development records.

| Team member | Responsibilities and actual contributions | Evidence |
| --- | --- | --- |
| [ThomasChoi2026](https://github.com/ThomasChoi2026) | Project design, classroom MVP, Notebook preparation and integration; requirements and prompts for classroom analysis and code comparison; system integration and testing | [Classroom MVP](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/commit/4fb68b0921305a08e3cad88a62193acf9f17237e), [Notebook preparation](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/commit/a7dda8450da2b95796ecc2d80550e4aaa537a7d5) |
| [aries36white](https://github.com/aries36white) | One-click student-editor source handoff to external OPT CPP; teacher-interface English localisation | [PR #3](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/3), [PR #24](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/24) |
| [superlulu77](https://github.com/superlulu77) | Starter-code reset, `.cpp` download, timestamped submission receipts, selected-task CSV export and Run-result copying | [PR #1](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/1), [PR #20](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/20) |
| [godferywong098kirito-blip](https://github.com/godferywong098kirito-blip) | Student submission history; English localisation of student-facing controls and related server messages | [PR #2](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/2), [PR #23](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/23) |
| [Mizunonamae](https://github.com/Mizunonamae) | Teacher classroom management, student removal and praise, and macOS build compatibility fix | [PR #4](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/4) |
| [isferr](https://github.com/isferr) | Weekly timetable and overlap detection; full-platform English localisation and documentation translation | [PR #5](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/5), [Translation commit](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/commit/6005885d5f9ad5fbe9e5103ad517898652cf738c) |

The team collaborated through feature branches, pull requests, integration and automated regression checks. The English localisation contributions were integrated through [PR #25](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/25). The table identifies formal group membership rather than claiming that no other contributor assisted the project.

[Complete main history](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/commits/main/) · [Pull requests](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pulls) · [Contributors](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/graphs/contributors)

## Documentation

| Guide | Purpose |
| --- | --- |
| [Running ClassLab](docs/RUN_CLASSLAB.md) | Official startup and school-server setup |
| [Notebook Classroom Integration](docs/NOTEBOOK_CLASSROOM.md) | Exact markers, metadata schema, examples and teacher-only content |
| [Coursework Demonstration](docs/COURSEWORK_DEMO.md) | Repeatable classroom rehearsal |
| [Course Delivery](docs/COURSE_DELIVERY.md) | Student controls, architecture and development review |
| [Native Judge Acceptance](docs/PHASE_4.md) | Isolation, resource controls and deployment verification |
| [Interactive Run](docs/INTERACTIVE_RUN.md) | Persistent sessions, stdin/EOF, limits and acceptance |
| [Project Context](docs/PROJECT_CONTEXT.md) | Development context and handoff |

## Acknowledgements

### Special thanks to Professor Chung Chan

We would like to express our sincere appreciation to **Professor Chung Chan**, our instructor for CS2310 Computer Programming at City University of Hong Kong.

ClassLab grew out of our experience of learning C++ through the course's notebook-based teaching, debugging activities and program visualisation. Professor Chan's teaching and his development of [OPT CPP](https://github.com/dive4dec/OPT_CPP) helped inspire our exploration of how students' individual coding activities could be connected more closely to the feedback available to an instructor during a lecture.

We hope ClassLab can complement his existing teaching approach by bringing notebook preparation, interactive exercises, code submissions and classroom feedback into a continuous workflow. We are grateful for his teaching, the inspiration provided by OPT CPP, and the opportunity to explore this idea through the Agentic Coding Group Project.

### Technical credits and references

ClassLab links to Professor Chan's OPT CPP as an external program visualiser ([original author credit](https://github.com/dive4dec/OPT_CPP/commit/f8b60a93e15139831546a4e4d7c37a39fe217354)). OPT CPP builds on the program visualisation work of Python Tutor. ClassLab implements its own classroom workflow, notebook integration, submission records, analytics and Judge integration; it does not distribute OPT CPP or Python Tutor runtime source or WASM assets.

- [OPT CPP — DIVE4DEC](https://github.com/dive4dec/OPT_CPP)
- [Python Tutor](https://pythontutor.com/) · [C++ visualiser](https://pythontutor.com/cpp.html) · [Link integration guide](https://pythontutor.com/for-ai-assistants.html)
- Guo, P. J. (2013). *Online Python Tutor: Embeddable Web-Based Program Visualization for CS Education*. SIGCSE '13, 579–584. [DOI: 10.1145/2445196.2445368](https://doi.org/10.1145/2445196.2445368).
- [cpp-httplib v0.28.0 — MIT](https://github.com/yhirose/cpp-httplib/tree/v0.28.0)
- [nlohmann/json v3.12.0 — MIT](https://github.com/nlohmann/json/tree/v3.12.0)
- [qrcode-generator 1.4.4 — MIT notice](web/vendor/qrcode.LICENSE)

ClassLab is an independent student coursework project. These acknowledgements and references do not imply participation, sponsorship or formal endorsement by the instructor or third-party developers.

---

**ClassLab — Connecting teaching, coding and classroom feedback.**

City University of Hong Kong · CS2310 · 2026
