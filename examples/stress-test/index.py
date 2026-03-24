#!/usr/bin/env python3
"""Stress test example for pyinkcli."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))


def _load_main():
    module_path = Path(__file__).with_name("stress-test.py")
    spec = importlib.util.spec_from_file_location("pyinkcli_examples_stress_test", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load stress test example from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main


if __name__ == "__main__":
    _load_main()()
