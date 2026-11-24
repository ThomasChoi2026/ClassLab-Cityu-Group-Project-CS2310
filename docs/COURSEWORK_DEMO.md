# ClassLab CS2310 coursework demonstration guide

## What the demo shows

Select **Demo run (replay)** on the student page to see a prerecorded result. Notebook import, classroom joins, code submissions, and teacher feedback happen live. The demo recognizes a fixed set of reviewed sample programs and inputs. Both runs and grades are labeled as replays. Native execution requires a verified isolated judge. Students can also open the team's external OPT CPP visualizer with one click.

## 1. Start the demo

From a clean clone or a temporary worktree, run:

```bash
bash demo/start_coursework.sh 8082
```

The script builds ClassLab, runs CTest, and starts a temporary demo server at `127.0.0.1:8082`. It uses a separate classroom data file and removes it when you press Ctrl+C. The demo runs without Docker, gVisor, a hosted website, or a domain.

In GitHub Codespaces, open **Ports**, forward `8082`, set its visibility to **Private**, and select **Open in Browser**. Only viewers authorized to access the private port can open it. If the browser preview fails, check the server from the terminal:

```bash
curl -fsS http://127.0.0.1:8082/api/health
```

If the response differs from `{"status":"ready","demo":true}`, check the startup log. If the response is correct but the browser cannot connect, check Codespaces private port forwarding.

If your existing checkout has uncommitted changes, use a separate worktree for this English submission:

```bash
git fetch origin submission/english
DEMO_DIR=$(mktemp -d /tmp/classlab-coursework.XXXXXX)
git worktree add --detach "$DEMO_DIR" origin/submission/english
cd "$DEMO_DIR"
bash demo/start_coursework.sh 8082
```

This creates a separate checkout and preserves any uncommitted work in your original checkout.

## 2. Load the teaching notebook

Select **Download teaching notebook (74 cells / 5 exercises)** in the yellow teacher banner, or download [CS2310 — From Control Flow to Procedural Abstraction](../examples/CS2310_Score_Analysis.ipynb) to the teacher's device. This original notebook contains five interactive exercises across 74 cells. Reference solutions and fixture results are kept in a separate instructor JSON file outside the classroom HTTP service.

| Original cell | Interactive exercise |
| --- | --- |
| 22 | Fix the grade boundary |
| 35 | Debug the accumulation loop |
| 48 | Find the maximum correctly |
| 63 | Fix the average function |
| 72 | Complete the score analyser |

Open **Lesson preparation** on the teacher dashboard and select the file. The initial filter shows the five interactive exercises. Select the first to load its title, description, starter code, five tests (three public and two hidden), and expected pitfall. Review the fields and select **Publish as current task**. Expand the cases, pitfalls, or exercise library when needed. The earlier synthetic exercise is retained for compatibility and regression tests. Its download link and preset-case button have been retired.

## 3. Demonstrate a run and collect submissions

1. Open three independent browser sessions and join the classroom using the QR code or join link.
2. As Student 1, select **Demo run (replay)**, enter the public boundary input `60`, and replay. The starter uses `score > 60`, so its output is `FAIL`. Submit that version to record its fixture grade.
3. As Students 2 and 3, change the condition to `score >= 60`. Replay with `60`, check the `PASS` output, and submit.
4. Show the dashboard with three submissions, two passes, and one failure. Open the shared edit and use the boundary test and expected pitfall to explain why equality matters.
5. Select the next exercise from the notebook already open on the teacher page.

All five exercises have replays for exact matches to the starter or reference source. CTest separately compiles and checks the examples offline with C++20. Demo runs accept public preset inputs. Submission replays also use hidden tests, whose statuses are visible to students. A different implementation, even a correct one, a changed test set, or an unrecognized input may have no matching fixture. Executing arbitrary student code requires the verified native judge.

## 4. 60-second English demonstration script

| Time | On-screen action | Script |
|---|---|---|
| 0–12 s | Import the notebook and show 74 cells and 5 exercises. | “A full teaching notebook may contain dozens of cells. ClassLab recognizes just the five interactive exercises.” |
| 12–24 s | Select cell 22, review the prefilled task and tests, and publish. | “I select the boundary exercise. The specification, starter and tests are loaded automatically; I decide when to publish.” |
| 24–39 s | Join by QR code, run with `60`, and change `>` to `>=`. | “The boundary fails before the fix and passes afterward. The demo results are clearly labeled prerecorded fixtures.” |
| 39–54 s | Show the 3/2/1 counts and open the shared edit. | “The class submits live. The dashboard identifies the shared correction and the test failure.” |
| 54–60 s | Select the next exercise. | “The notebook stays open, so the teacher can move to the next activity without re-importing it.” |

**Q&A:** “All five fixture variants were checked by real C++20 tests offline. The live demonstration does not execute arbitrary student code; unrestricted execution requires a validated isolated Judge.”

## 5. Acceptance checks and limitations

```bash
ctest --test-dir build --output-on-failure
# With the demo running in a separate terminal:
python3 tests/browser_notebook_classroom.py http://127.0.0.1:8082 --evidence-dir notebook-evidence
```

The browser test needs Playwright, Chromium, Pillow, and zxing-cpp. The `notebook-classroom.yml` GitHub Actions workflow installs them and checks file import, the 74-cell/five-exercise filter, unsaved-edit protection, privacy, input on first run, submissions, and teacher totals. It also runs the existing QR and browser regressions.

**Arbitrary student programs require a separately verified gVisor judge.** If live execution of arbitrary C++ is part of the assessment, the prerecorded demo covers only the classroom workflow.
