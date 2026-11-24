"""Actual-host interactive acceptance; do not run before full PHASE_4 approval."""
import argparse
import sys
import tempfile
import threading
from pathlib import Path

from workflow import server
from interactive_scenarios import check

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"judge"))
import worker
from interactive import Manager

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--runtime",choices=("runsc","runc"),default="runsc")
    parser.add_argument("--operator-verified",action="store_true")
    args=parser.parse_args()
    if not args.operator_verified:
        parser.error("First pass the full original isolation acceptance on a dedicated approved host.")
    worker.RUNTIME=args.runtime
    if not Path(worker.DOCKER[0]).is_file():
        worker.DOCKER[0]="/usr/bin/docker"
    worker.verify_runtime()
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)
        sock=path/"judge.sock"
        sessions=Manager(worker.sandbox_session,idle=8)
        with worker.Worker(str(sock),sessions) as service:
            thread=threading.Thread(target=service.serve_forever)
            thread.start()
            try:
                with server(path/"rooms.json",sock) as base:
                    check(base)
            finally:
                service.shutdown()
                thread.join()
        assert not sessions.failed
    print("Interactive functional acceptance passed. Verify actual resource limits and cleanup per PHASE_4 before enabling the extra operator flag.")

if __name__=="__main__":
    main()
