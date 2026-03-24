"""Entry point for terminal-resize example."""

import runpy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("terminal-resize.py")), run_name="__main__")
