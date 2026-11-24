"""Real GCC interactive HTTP API acceptance with fixed reviewed sources."""
import shutil
import sys
import tempfile
from pathlib import Path
from workflow import server
from interactive_scenarios import FIXED, check
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"judge"))
from trusted_native import NativeEvaluator, approved_sources, native_socket

def main():
    compiler=shutil.which("g++")
    assert compiler
    sources=approved_sources()
    sources.update({s:s for s in FIXED})
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)
        sock=path/"judge.sock"
        with native_socket(sock,NativeEvaluator(compiler,sources),idle=8),server(path/"rooms.json",sock) as base:
            check(base,native=True)

if __name__=="__main__":
    main()
