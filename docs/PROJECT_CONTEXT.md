# ClassLab project background and handover

Background last updated on 22 November 2026. This document records project-level decisions from earlier ChatGPT and Codex sessions for teammates and new Codex Cloud tasks. It excludes the contents of private course materials.

## Delivery scope

ClassLab is a coursework project. GitHub holds the reproducible source, Codex Cloud is used for development and testing, and a temporary private preview supports acceptance and demo recording. The environment can be stopped after recording. Prefer free resources. Public deployment, commercial accounts, and long-term operation are outside the coursework scope. The plans and historical notes below are retained for context. For current teacher and student instructions, see the [development and review guide](COURSE_DELIVERY.md). Server-side execution of student code requires a separate judge that has passed isolation checks. External OPT CPP is for practice.

## 1. Project purpose

**ClassLab** is a live, interactive programming classroom for the City University of Hong Kong CS2310 Computer Programming Agentic Coding Project.

A teacher presenting C++ in a Jupyter Notebook can share the current example or a debugging exercise. Students scan a QR code or open a link on a phone, tablet, or computer, receive the task without copying from the projector, edit it, submit, and see the result. The teacher follows joins, attempts, submissions, and passes to decide where the class needs more explanation.

The design focuses on the classroom workflow. Jupyter and VS Code already execute notebook cells. A general quiz app, a single-concept game, or another notebook execution environment would not address the teaching problem.

The intended one-minute demonstration starts with a teacher publishing a buggy C++ program. Two students receive it immediately, edit it, and submit different answers. The teacher uses the resulting statuses and counts to discuss the class's progress.

## 2. Decisions already made

- The project is named ClassLab.
- Target repository: [ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310).
- When first inspected, the private repository used `main` as its default branch and contained a short README. Check the current files and branch state at the start of new work.
- The user chose the GitHub-connected Codex Cloud environment for this project. Development and storage on the Mac are outside the project workflow.
- A separate local workspace called CS C++ contains private slides, notebooks, exercises, and backups. An earlier Codex session mistook it for the project directory and scanned unrelated files. Do not copy, commit, or upload that material.
- An empty `~/Projects/ClassLab` directory was once created locally after an unsuccessful clone. It is not a project dependency. Do not access it to resume the work.
- C++20 was selected as the initial backend standard. The student grading standard should be independently configurable, initially defaulting to C++20.
- The planned frontend uses HTML, CSS, and JavaScript. The first phase can run without a Node.js build toolchain.
- Product features do not need a large language model. Developers may use Codex.
- Early project discussions and documentation used Chinese. This submission uses English.

## 3. Original MVP requirements

Check the current repository for the implementation status of each requirement.

### Teacher

1. Create a classroom session and obtain its link and QR code.
2. Publish a C++ task with starter code and machine-checkable tests.
3. View the number of students who joined, submitted, and passed, together with the latest submission results.

### Student

1. Join a specific classroom by link or QR code without registering. A nickname or temporary session identifier is sufficient.
2. Receive, view, edit, and submit starter code in the browser.
3. See compilation and test results while keeping the teacher's hidden test data private.

### System

1. Store tasks, submissions, and grading status. A simple persistence method or in-memory storage is acceptable for the MVP if its limits are documented.
2. Compile, run, and check submitted C++ in isolation with time and resource limits.
3. Send statistics to the teacher page. Periodic HTTP polling is sufficient for the MVP.
4. Give clear feedback for invalid input, duplicate submissions, missing classrooms, and execution failures.

Before isolation is verified, use read-only simulated data or controlled examples to validate the interface and workflow. Do not expose direct execution of arbitrary student programs on the public internet.

## 4. Outside the initial MVP

- A JupyterLab extension that publishes the current teaching cell in one click.
- Deep integration with Canvas, DIVE, E-Quiz, or other university systems.
- Automatic student-account notifications or mobile push notifications.
- AI-generated exercises, AI grading, and AI tutoring.
- Multilanguage judging, full course management, and advanced teacher analytics.

Interfaces can allow for future extensions. Mark these ideas as future work unless the repository demonstrates an implementation.

## 5. Initial technical recommendations

- **Architecture.** A C++20 service handles classrooms, tasks, submissions, and statistics. Use a separate isolated runner and static teacher and student pages.
- **Build.** Use CMake and established, readily installable HTTP and JSON libraries.
- **Communication.** Use HTTP and JSON. Start with polling for teacher statistics.
- **Hosting.** Develop and test in the cloud. Verify the demo address on a phone if needed. Development workspaces are temporary.
- **Grading.** Compare output against expected results or teacher-defined tests, with resource limits and isolation. Successful compilation alone does not demonstrate a correct solution.
- **Git.** Inspect the repository for each task. Work on a separate branch. Push, open a pull request, or merge according to the user's current authorization and the capabilities of the connected environment.

## 6. Lessons from the earlier discussions

### Project selection

- The user rejected ideas such as guessing a black-box function or practicing one narrow concept. The project should improve everyday teaching, participation, and convenience.
- Jupyter and VS Code already run cells. The classroom value comes from quickly sharing material already being taught, enabling students to take part, and showing feedback to the whole class.
- Online judges and classroom interaction products already exist. Avoid claims of being the first. Test how readily teachers can publish from their existing materials.

### Earlier Codex session

- The initial task ran in the private CS C++ workspace and inspected unrelated files. There was no evidence that any course materials were uploaded.
- Local Git authentication failed for the private repository. GitHub browser or ChatGPT connector authorization and terminal Git credentials are separate.
- The user chose cloud development directly against GitHub and no longer needs a local Mac checkout.
- If the environment is macOS and the working directory is the private CS C++ workspace, stop editing there and use the selected Codex Cloud project environment.
- The confirmed decisions and facts are sufficient for handover. There is no need to upload full transcripts. Verify the current repository state when resuming work.

## 7. Recommended development sequence

1. **Repository setup.** Confirm the connected repository, inspect its README, files, and Git status, then establish the smallest project structure with a README, appropriate `.gitignore`, CMake configuration, and a compilable test.
2. **Sessions and publishing.** Let teachers create a classroom and publish starter C++ that students can immediately see by link. Verify the end-to-end connection.
3. **Editing and submission.** Add browser editing, saved submissions, and teacher-visible submission activity.
4. **Isolated grading and feedback.** Compile and execute safely, run tests automatically, and report pass/fail reasons. Keep the runner separate from the web service.
5. **QR codes, statistics, and acceptance.** Test teacher progress, QR scanning, mobile use, and integration.
6. **Submission and release.** Prepare the README, run and test instructions, screenshots of functioning features, and a one-minute demonstration. Use a branch or pull request for review.

The coursework deadline was set for 24 November 2026 at 23:59 Hong Kong time. A stable, complete demonstration takes priority over extensions.

## 8. Suggested prompt for the original setup task

Read `AGENTS.md` and `docs/PROJECT_CONTEXT.md`, then inspect the connected GitHub repository and its existing files. Initialize only the first-phase foundation: a README, CMake, a minimal C++20 program, `.gitignore`, and essential instructions. Leave automatic grading, Jupyter extensions, and additional features to later phases. Compile and test the result. Report changes, test outcomes, open issues, and branch or pull request status. Do not copy private materials, visit the Mac's private CS C++ directory, or merge into `main` without authorization. Stop and report if the connected repository is not the specified project.

## 9. Questions recorded at the initial handover

- Is the selected cloud environment connected to the intended repository, and is it reusable?
- Which files have been added since the first README?
- Which small C++ HTTP and JSON libraries should be used, and how will students reach the demo URL from phones?
- Can the proposed grading isolation run and pass acceptance in Codex Cloud or on the deployment host?
- How will teammates divide the work, and what are the final demonstration requirements?
