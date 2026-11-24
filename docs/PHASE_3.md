# Phase 3 acceptance and grading boundaries

> Historical Phase 3 record. For the later Judge adapter and its deployment requirements, see [Phase 4](PHASE_4.md). For current student features, see the [student workflow](COURSE_DELIVERY.md#student-workflow).

## Classroom workflow demonstrated in this phase

Teachers create a classroom, project its QR code, and add public or hidden cases before publishing. Students can expand the public examples, edit the starter code, and submit. The dashboard shows counts for students who have submitted, those who have yet to submit, and ungraded attempts. Authorized teachers can open each student's latest submission for the current task. Publishing another task creates a new snapshot and keeps prior tasks and submissions in the data file. Refreshing the student page restores their identity, draft, and latest submission status for the current task.

A graded task has 1–12 cases. Each case needs a name, visibility, input text, and expected output text. Either text field may be empty. A task without cases collects submissions only. Published cases cannot be edited in place. Unit tests cover output comparison: normalize CRLF to LF, ignore one final LF, and compare all remaining characters, including spaces and newlines. Live Phase 3 submissions did not invoke this comparator.

## Results and statistics

- ClassLab reads persisted latest grading records and distinguishes runner outages, service errors, wrong answers, and other verdicts. Public cases may expose actual output. For a hidden case, the student receives only a generic number and status. The classroom's original case ID, name, input, expected and actual output, and runtime error text stay private.
- Teacher statistics count each student's latest formal submission for the current task. The pass-rate denominator includes only conclusive verdicts. Runner outages and system errors count as ungraded. Each test's pass rate uses only students with a pass or fail record for that case. A case skipped after a compilation failure contributes nothing to the denominator.
- Diagnostic categories use recognizable patterns in the compiler's first error line. Teachers can inspect a representative message and the original submission. The category is a clue for review. Students who fail the same case may have made different mistakes.
- Phase 2 data needs no migration. Older tasks without cases still collect code, and submissions without a grading record still show as submitted. Phase 3 stores case snapshots and ungraded status separately. Automated tests load synthetic fixtures only into temporary data files. The standard service does not create demo grades.

## Execution checks and probe results

In the Phase 3 cloud environment, Docker started a trusted BusyBox probe under runsc with an unprivileged UID, dropped capabilities, a read-only root filesystem, and no external network interface. The probe observed UID 65534, zero effective capabilities, only loopback networking, and a read-only root mount. It could not see the workspace, Docker socket, or checked environment variables for GitHub, SSH, or cloud credentials. The runtime separately mounted writable `/tmp` with roughly 16.6 GiB available. The file write limit also exceeded the requirement. Docker reported rootless mode, no cgroup driver, and `--ignore-cgroups` for runsc. Effective CPU, memory, and process limits could not be verified. Direct user-namespace and Bubblewrap attempts on the host failed to write the UID mapping.

Live execution therefore stayed disabled in Phase 3. An authenticated student sending the current task ID, source, and custom stdin to `POST /api/rooms/{room}/run` received HTTP 503 with `judge_unavailable`. The request neither executed code nor created a submission. `POST /api/rooms/{room}/submissions` saved the code with an explicit ungraded status. Repeating the same source for the same student, task, and request ID did not increment the attempt count.

The next phase called for a dedicated runner with verifiable controls for both compilation and execution. Required checks cover CPU, memory, process, file and output limits, wall-clock timeouts, cleanup, read-only and temporary filesystem boundaries, credentials, classroom data, control sockets, external networking, and concurrency. The judge should run outside the web service with a pinned compiler and isolated runtime. Each test needs its own temporary workspace so hidden data and state cannot reach public output. Only trusted workers should record results, after validating statuses and case IDs and limiting output and diagnostic lengths. End-to-end isolation for infinite loops, resource abuse, and access to restricted resources was **not verified** in this phase. Compilation errors, wrong answers, and crashes from a real runner also awaited end-to-end verification.

## Acceptance and privacy

Use the CMake and CTest commands in the README. Integration tests cover authorization, test-case validation, hidden data filtering, concurrency, deduplication, restart recovery, task changes, and runner outages. Clearly identified synthetic records check the student-facing results and classroom statistics. Use private port 8080 in the existing Codespace. Phones need GitHub authorization for the same preview. Record with sample tasks and demo nicknames. Before using a shared classroom, confirm preview and data-file access, test content, and submission retention. Classroom trials with automatic grading require a verified runner.
