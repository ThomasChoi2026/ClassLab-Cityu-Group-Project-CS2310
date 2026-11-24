# Interactive free Run; batch Submit

The private Judge socket advertises interactive capability only when enabled. The web API authenticates the student and classroom and binds each random session ID to that student and task. HTTP polling every 350 ms reads bounded cumulative stdout/stderr. Send appends a newline if needed, EOF closes stdin after pending bytes drain, and Stop terminates. The same process remains alive; no source or prompt scanning is used. Pipe buffering follows C/C++ rules; flush prompts explicitly when needed. Separate streams preserve their own order, not a total order.

Limits: two interactive sessions per worker, one per student; 8 KiB cumulative input; 16 KiB per output stream; 30 seconds without input/output activity (not proof of stdin waiting); 90 seconds absolute running time; CPU time 3 seconds soft/4 hard; bounded compilation and startup. Results expire after 120 seconds. Abandoned sessions stop at independent deadlines. Task change stops the browser's old session; new input for an inactive task is refused. Input is never automatically retried after a lost response. Submit remains the existing batch queue.

## Sandbox
Default: complete-stdin batch Run. The interactive backend uses the original pinned compile and execution containers, existing preflight, cgroups, network isolation, user, mounts, read-only root, and forced cleanup. It adds a CPU-time limit and keeps Docker attach stdin open. Docker runtime EOF and CPU-limit behavior must be validated on the actual dedicated host. First pass all PHASE_4 tests, then run the additional acceptance described below, including cleanup and resource controls. Only then add the additional --interactive-operator-verified flag to the existing --operator-verified invocation. Never bypass either acceptance in Codespaces. If actual-host tests fail, leave the extra flag off.

## Native experiment
Only the exact locally reviewed source from the approved list is eligible for real execution. No sandbox is claimed. Do not approve unreviewed source or expose the worker publicly.

## Actual-host test
After all original PHASE_4 checks pass on the approved host, build and run:

~~~sh
python3 tests/interactive_sandbox.py ./build/classlab --runtime runsc --operator-verified
~~~

Confirm CPU/memory/PID limits, EOF delivery and no leftover labeled containers on the actual host. This is not an ordinary cloud CI test. Only enable the additional flag after actual-host acceptance. Default remains complete-input batch Run.
