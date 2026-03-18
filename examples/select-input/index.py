"""Entry point for select-input example."""

import runpy
from pathlib import Path


if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("select-input.py")), run_name="__main__")
