"""Entry point for static example."""

import runpy
from pathlib import Path


if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("static.py")), run_name="__main__")
