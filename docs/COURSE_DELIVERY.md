# ClassLab development and review guide

## Project overview

ClassLab helps a teacher turn a C++ example from a notebook into a classroom debugging exercise. The teacher selects a code cell, adds instructions and optional test cases, then projects a join QR code. Students use a browser to edit and submit. The teacher can follow participation and, when adjudicated results exist, see which tests or compiler diagnostics are common across the class.

## Install and run

Use `main` to review the latest verified version and as the baseline for new work. Use the corresponding feature branch to review a specific development stage. Use Linux or WSL with a C++20 compiler, CMake 3.24 or later, Python 3, and network access to fetch the pinned C++ dependencies on the first build. CTest also runs the line-diff regression test when Node.js is available.

~~~sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure
~~~

Run the standard classroom server with ./build/classlab. Open http://127.0.0.1:8080 in the server's browser or open port 8080 through an existing private Codespaces preview. To demonstrate on another device, use the same preview URL with a GitHub account already authorized for that port.

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
- The C++20 server handles classroom membership, role checks, submissions, the persistent queue, and dashboard aggregation. Hidden tests stay within teacher-authorized paths, and the projection displays classroom totals.
- The normal Judge uses a private Unix socket and independent containers with a pinned GCC image. The execution service requires deployment acceptance before it can run arbitrary student programs. Phase 5 exercised real GCC with a trusted-source allowlist and verified results through the browser. Full runtime isolation acceptance for arbitrary submissions, including cgroup quotas and resource-exhaustion handling, remains outstanding.
- Demo mode records real joins, edits and submissions against a temporary store. It replays fixed results for the published synthetic exercise. It disables free-form execution and labels replay results on both sides. It works without Docker, a compiler in the browser, student credentials, or external services at runtime.

## Development review and collaboration

| Criterion | Evidence and remaining handoff |
| --- | --- |
| Published | Share the private feature branch link and exact commit for review. Verify reviewer access. |
| Documented | English overview, setup, architecture, limitations and demo script are in this guide. Keep the guide current as the workflow changes. |
| Functional | Build and run CTest, rehearse the private demo, and distinguish the replay from the prior real GCC evidence. Keep arbitrary execution disabled until isolation acceptance. |
| Innovative | The contribution is the lesson workflow from a notebook cell to immediate participation to class-level feedback. QR codes, compilation and test judging are established techniques. |
| Teamwork | Assign reviewers for the Notebook workflow, privacy checks, and rehearsal. Record only actual contributions. The Phase 5 baseline's Git author labels list seven commits under Thomas CAI and one under ThomasChoi2026. This establishes commit attribution only. Record any confirmed offline work separately. |

Start each task from the latest `main` on a separate feature branch. Commit and push that branch, then share its GitHub compare link for review. Merge verified and reviewed changes into `main` with their history intact. Keep the existing history and author metadata. Record only confirmed contributors and reviewers.

## 60-second English demo script

| Time | Show | Say |
| --- | --- | --- |
| 0–10 s | Teacher editor and synthetic Notebook | “A teacher already has an example in a notebook. Turning it into a shared debugging task usually breaks the flow of the lesson. ClassLab keeps that workflow in one place.” |
| 10–23 s | Select the buggy cell, publish, then open Classroom View | “I choose a C++ cell, add instructions and test cases, and publish it. The notebook stays in my browser. Students get the selected exercise through this QR code.” |
| 23–38 s | Student views and their code changes | “Students join from a browser, edit the exercise, and submit. The projection updates as their submissions arrive.” |
| 38–53 s | Common edit and line diff | “Two students changed subtraction to addition. Here is the line they edited and the test result for each submission. The verdicts are fixed replays. The submissions and class counts are live.” |
| 53–60 s | Return to Classroom View | “The goal is to help the teacher decide what to explain next while the class is still working.” |
