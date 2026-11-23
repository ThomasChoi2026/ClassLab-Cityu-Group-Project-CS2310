#!/usr/bin/env bash
# Safe coursework presentation: only explicitly labeled prerecorded verdicts.
# Never starts a live Judge or executes untrusted student C++.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${1:-8082}"
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || (( PORT < 1 || PORT > 65535 )); then
  echo "Usage: bash demo/start_coursework.sh [port 1-65535]" >&2
  exit 2
fi
cd "$ROOT"
echo "== ClassLab Coursework Demo (PRELOADED REPLAY; not real C++ execution) =="
echo "== Build and automated tests =="
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure
echo "== Classroom demo =="
echo "Open port $PORT with Codespaces Ports (PRIVATE only), or use http://127.0.0.1:$PORT"
echo "This server binds to 127.0.0.1 and writes classroom data only to a temporary directory."
echo "Teacher banner: download CS2310 teaching Notebook; import Cell 2, load demo cases."
echo "Student: use Demo Run, enter 2 3, view explicitly labeled prerecorded result."
echo "Ctrl+C stops server and removes temporary data."
exec python3 demo/run.py --port "$PORT"
