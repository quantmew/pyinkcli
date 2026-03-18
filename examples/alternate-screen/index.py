"""Entry point for alternate-screen example."""

import runpy
from pathlib import Path


if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("alternate-screen.py")), run_name="__main__")
