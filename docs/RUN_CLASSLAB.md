# Running ClassLab — trusted native experiment

Build using the README instructions. This branch has no replay runtime. Its native runner uses real GCC without per-program containment, restricted to reviewed exact sources. Use only a non-root, private test environment with no sensitive data. Do not expose it publicly or approve unreviewed sources. Start:

~~~bash
python3 judge/trusted_native.py --trusted-local-only --port 8080
~~~

The 74-cell teaching Notebook and reference sources are approved at startup. Additional locally reviewed files may be added with `--approve-source`. Code and input are genuinely compiled/executed and verdicts are calculated from actual output; an unapproved source is saved but not executed. Basic time and resource limits do not provide a sandbox. Classroom data is separate at `data/trusted-native-classrooms.json`. For arbitrary student submissions use the isolated Judge in the sandbox-only branch, following [PHASE_4.md](PHASE_4.md).

Free Run now uses a persistent interactive session. Click Run, then send one or more lines, send EOF explicitly, or stop. The compiled process stays alive between sends; Submit still uses the original batch grader. See [interactive Run](INTERACTIVE_RUN.md).
