"""Entry point for box-backgrounds example."""

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("box-backgrounds.py")), run_name="__main__")
