# Phase 4 execution and deployment acceptance

> This guide covers the ClassLab server-side Judge. The optional [OPT CPP handoff](COURSE_DELIVERY.md#opt-cpp-practice) is a browser link. It does not provide formal judging or change the server's isolation requirements.

## Architecture and scope

ClassLab retains its C++20 web service and classroom data. A separate Python 3 judge receives source and standard input over a local Unix socket. It uses Docker and gVisor to run GCC 14.3.0 with `-std=c++20` in a separate process. The image is pinned by digest and is never pulled during execution. Compilation gets a dedicated container. Each test gets a fresh container and workspace. Expected outputs stay in the C++ service, which applies the Phase 3 newline comparison rules. Hidden-case output is discarded. Students receive only a generic case number and status.

The team considered three approaches. Server-side execution needs a verified runtime, filesystem isolation, and effective cgroup v2 controls, which the evaluated Codex Cloud host lacked. A separate judge keeps privilege boundaries and can use self-hosted components. Services such as Judge0 have additional service and isolation requirements, so the team chose a local Python standard-library worker. Browser WebAssembly practice would require a distributable, pinned C++20 toolchain and standard library, plus checks for input/output, memory, and browser compatibility. Browser results cannot serve as trusted classroom grades. Phase 4 did not implement this route. The later OPT CPP browser feature uses an external tool.

## Runtime configuration

Use an approved, dedicated Linux x86-64 host with a local Docker daemon and effective cgroup v2 CPU, memory, and PID controllers. The default runtime is gVisor runsc. If the target gVisor setup fails its probes, evaluate runc only on a dedicated VM without sensitive data, under the same acceptance criteria. runc shares that VM's kernel. Keep the Docker host or daemon free of other workloads and data. Install trusted Docker and gVisor, register runsc with Docker, and verify that the runtime enforces cgroups. The judge user needs privileged daemon access and must be separate from the classroom web user. Student containers must have no host-path, Docker socket, credential, or classroom-data mounts. Verify the available privileges on any Codespaces host.

1. Review the image source and pull the pinned image on the target host:

   ~~~sh
   docker pull --platform linux/amd64 docker.io/library/gcc@sha256:5e927c284bf55a7dc796262e311a0703344f62f41f5621eb56843111b1d37e15
   ~~~

2. Run the probes and acceptance checks as the actual judge user. Keep execution disabled if any check fails.

   ~~~sh
   python3 judge/worker.py
   python3 tests/judge_smoke.py --acceptance
   python3 tests/judge_real_flow.py build/classlab
   ~~~

3. Check the startup probe, acceptance script, and effective configuration. The probe checks visible host cgroup quotas, root mounts, UID, capabilities, NoNewPrivs, networking, temporary disk limits, and file size limits. Acceptance also covers CPU throttling, memory and process limits, denied access to test markers and services, compile and run timeouts, and cleanup after forced termination. Check Docker for proxy-injected credentials and application mounts, and verify workspace isolation between cases. Restart and revalidate after infrastructure or cleanup failures.

4. On the same host, use `judge/classlab-judge.service` as a systemd example. It assumes installation under `/opt/classlab` and a separate `classlab-judge` user and group. An administrator creates the accounts and installs the service. Give the web user socket access through the `classlab-judge` group. The judge uses a private `/run/classlab-judge` directory. On shutdown, `ExecStopPost` removes containers labeled by this dedicated worker. Use `--operator-verified` only after acceptance. For runc, pass `--runtime runc` to the probe, acceptance checks, and service.

5. Start ClassLab with `CLASSLAB_JUDGE_SOCKET=/run/classlab-judge/judge.sock`. Keep the web preview private and do not forward the judge socket. The page enables Run according to current judge availability. When the judge is unavailable, Run returns 503. Submit saves the source and displays an ungraded result.

## Standard input and interactive execution

The official application never enables unisolated execution. An accepted batch worker accepts complete stdin supplied before Run. The browser no longer probes and reruns. The legacy private probe protocol remains only for compatibility and regression tests.

Interactive execution requires additional actual-host validation of persistent Docker attach stdin, EOF, cleanup and limits. Follow [INTERACTIVE_RUN.md](INTERACTIVE_RUN.md); use the additional operator-verified flag only after those tests pass. Submit remains batch evaluation.

## Execution and failures

The container requests one CPU, 256 MiB of memory without swap, 32 processes, an 8 MiB `/tmp`, a 16 MiB `/work`, and a 1 MiB per-file limit. It uses Docker's default seccomp policy, disables IPC sharing, and has no external network. Compilation and execution have 15-second and three-second wall-clock limits respectively. Docker management commands and the whole task have separate deadlines. The runner retains up to 16 KiB each of stdout and stderr and checks the size and ELF format of compiled artifacts. After a timeout or resource overrun it attempts forced container removal. Cleanup failures disable the judge, with an additional systemd stop hook for cleanup. The batch worker serializes ordinary runs and submissions. An additionally accepted interactive worker has two bounded free-run slots; each retains the same isolated process for input sends. Phase 5 queues formal submissions persistently. Practice runs ask students to retry when the worker is busy or submissions are queued. Startup failures count as service errors. Student compile and run deadlines begin after trusted confirmation of container startup. Formal results update by submission ID. Queued attempts resume after restart, while interrupted grading becomes a service error and does not count as a wrong answer.

## Test evidence

- CTest includes classroom and output-comparison tests plus Unix protocol integration with an explicit mock judge. It covers status validation, concurrency, recovery, authorization, and result storage.
- `tests/judge_smoke.py` runs only the fixed, trusted GCC examples by default. `tests/judge_real_flow.py` accepts only fixed programs and inputs on a temporary Unix socket and checks that actual results reach the C++ classroom statistics. Neither entry point starts the regular student execution service.
- In the evaluated Codex Cloud environment, Docker reported no cgroup driver and runsc was configured with `--ignore-cgroups`, so the production startup probe refused to enable execution. Effective CPU, memory, and process limits, resource abuse, and recovery after forced termination still needed verification on the acceptance host. Trusted probes confirmed an unprivileged UID, zero capabilities, a read-only root, loopback-only networking, 8 MiB `/tmp`, 16 MiB `/work`, the file-size ulimit, no repository or Docker socket mounts, and no-new-privileges via `prctl`. Keep execution disabled and do not run the `--acceptance` stress cases in that environment.
