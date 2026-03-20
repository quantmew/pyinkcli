"""Entry point for terminal-resize example."""

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("terminal-resize.py")), run_name="__main__")
