"""Entry point for use-focus-with-id example."""

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("use-focus-with-id.py")), run_name="__main__")
