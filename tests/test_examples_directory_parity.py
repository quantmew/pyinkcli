"""Directory-level parity checks for examples."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JS_EXAMPLES = ROOT / "js_source" / "ink" / "examples"
PY_EXAMPLES = ROOT / "examples"


def test_every_js_example_directory_has_python_directory() -> None:
    js_dirs = {
        path.name
        for path in JS_EXAMPLES.iterdir()
        if path.is_dir()
    }
    py_dirs = {
        path.name
        for path in PY_EXAMPLES.iterdir()
        if path.is_dir()
    }

    assert js_dirs <= py_dirs


def test_every_python_example_directory_has_main_files() -> None:
    for path in PY_EXAMPLES.iterdir():
        if not path.is_dir() or path.name == "__pycache__":
            continue

        index_file = path / "index.py"
        assert index_file.exists(), str(index_file)

        js_dir = JS_EXAMPLES / path.name
        js_non_index_files = [
            candidate
            for candidate in js_dir.glob("*.ts*")
            if candidate.name != "index.ts" and candidate.name != "index.tsx"
        ]
        py_non_index_files = [
            candidate
            for candidate in path.glob("*.py")
            if candidate.name != "index.py"
        ]

        if js_non_index_files:
            assert py_non_index_files, str(path)
