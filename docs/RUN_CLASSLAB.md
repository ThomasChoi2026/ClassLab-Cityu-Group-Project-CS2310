# Running ClassLab — isolated Judge and a school server

This branch uses the real classroom server with an optional security-accepted Judge. No replay launcher is included.

## 1. Build once

On a supported Linux or WSL machine, with Git, CMake 3.24+, a C++20 compiler, Python 3 and Node.js (for all CTest tests):

```sh
git clone https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310.git
cd ClassLab-Cityu-Group-Project-CS2310
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure
```

Initial dependency download needs network access. Repository access is required if it is private.

## 2. Normal ClassLab (without a Judge)

```sh
CLASSLAB_JUDGE_SOCKET= CLASSLAB_PORT=8080 ./build/classlab
```

Open http://127.0.0.1:8080 on the same machine, or privately forward port 8080 in Codespaces. This is the real application, not a simulation. Import Notebook files, create a classroom, receive actual student submissions, and analyze source changes. Without a Judge, Run is disabled and submissions are recorded without grading. Data persist in data/classrooms.json relative to the current directory by default. Protect and back up the file. 

## 4. Normal ClassLab with real C++20 execution (administrator setup)

A school server can host the normal version, but having a server alone does not guarantee safe student-code execution. The instructor or school IT administrator should follow the full [Judge deployment and security acceptance guide](PHASE_4.md). Use a dedicated approved Linux x86-64 environment, local Docker daemon with effective cgroup v2 CPU/memory/PID controls and registered gVisor runsc, separate Judge and web-service users, and no sensitive data or unrelated workloads on the Judge host.

After building the project, install the pinned GCC image and run the following **on the actual target host, as the intended Judge user**, from the project directory. Stop if any check fails; the acceptance tests must not be run on an unverified/unapproved host.

```sh
docker pull --platform linux/amd64 docker.io/library/gcc@sha256:5e927c284bf55a7dc796262e311a0703344f62f41f5621eb56843111b1d37e15
python3 judge/worker.py
# Only after successful preflight and operator approval:
python3 tests/judge_smoke.py --acceptance
python3 tests/judge_real_flow.py build/classlab
```

After all acceptance checks pass and the administrator has prepared the service accounts, group permissions and project location, use [judge/classlab-judge.service](../judge/classlab-judge.service) as the systemd service example. Its deployment directory is /opt/classlab and its socket is /run/classlab-judge/judge.sock. The service's operator-verified flag is an attestation of completed checks, not a bypass. The web service user gets access only to the private socket, not the Docker daemon.

For example, once the Judge is running and a private writable data directory /var/lib/classlab has been provisioned for the non-root web service user, launch the web binary **as that user**:

```sh
cd /opt/classlab
\
CLASSLAB_HOST=127.0.0.1 \
CLASSLAB_PORT=8080 \
CLASSLAB_DATA=/var/lib/classlab/classrooms.json \
CLASSLAB_JUDGE_SOCKET=/run/classlab-judge/judge.sock \
./build/classlab
```

Use a school-managed, authenticated HTTPS reverse proxy or approved internal access route to reach the web service. Students open the resulting classroom URL or scan the QR code. Do not publish the Unix socket or Docker daemon, and do not expose the application as an unrestricted public service: the current course MVP does not implement production-grade account management and rate limiting.

Create a small test classroom, and confirm the student's Run button enables, a no-input program produces output, an input program uses complete stdin supplied before batch Run, or accepts repeated input in one persistent process when the additional interactive deployment checks have passed, and formal submissions produce real verdicts. The deployment has not been certified merely because the repository CI is green. The native Judge needs actual-host acceptance, including isolation, resource limits, cleanup and failure recovery.

## Quick comparison

| Mode | Command | Classroom storage | Evaluation |
| --- | --- | --- | --- |
| Normal, no Judge | CLASSLAB_JUDGE_SOCKET= ./build/classlab | Persistent | Receives submissions; no execution |
| Normal, accepted Judge | CLASSLAB_JUDGE_SOCKET=/run/classlab-judge/judge.sock ./build/classlab | Persistent | Actual C++20 compilation/execution |

The sample Notebook and teaching workflow remain unchanged. No mode-switch button exposes or weakens the Judge from the browser.

For persistent interactive Run, follow [INTERACTIVE_RUN.md](INTERACTIVE_RUN.md). Keep batch Run enabled only after the original isolation acceptance; enable the additional interactive capability only after its own actual-host acceptance.
