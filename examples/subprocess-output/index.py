"""Entry point for subprocess-output example."""

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("subprocess-output.py")), run_name="__main__")
