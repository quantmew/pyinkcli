"""Smoke tests for representative examples."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from pyinkcli.ansi_tokenizer import tokenizeAnsi

ROOT = Path(__file__).resolve().parents[1]


def _strip_ansi(text: str) -> str:
    return "".join(token.value for token in tokenizeAnsi(text) if token.type == "text")


def _run_example(relative_path: str, timeout: float = 2.5) -> str:
    path = ROOT / relative_path
    completed = subprocess.run(
        [
            "timeout",
            f"{timeout}s",
            sys.executable,
            "-u",
            str(path),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    output = completed.stdout

    return _strip_ansi(output)


def test_select_input_example_smoke() -> None:
    output = _run_example("examples/select-input/index.py", timeout=1.5)
    assert "Select a color:" in output
    assert "Red" in output


def test_alternate_screen_example_smoke() -> None:
    output = _run_example("examples/alternate-screen/index.py", timeout=1.5)
    assert "Unicorn Snake" in output
    assert "Score:" in output


def test_static_example_smoke() -> None:
    output = _run_example("examples/static/index.py", timeout=1.8)
    assert "Completed tests: 0" in output


def test_subprocess_output_example_smoke() -> None:
    output = _run_example("examples/subprocess-output/index.py", timeout=4.0)
    assert "Сommand output:" in output
    assert (
        "ink@6.8.0 example" in output
        or "NODE_NO_WARNINGS=1 node --import=tsx examples/jest" in output
        or "PASS  tests/" in output
        or "FAIL  tests/" in output
        or "RUNS  tests/" in output
    )


def test_use_transition_example_smoke() -> None:
    output = _run_example("examples/use-transition/index.py", timeout=1.5)
    assert "useTransition Demo" in output
    assert "Results" in output


def test_cursor_ime_example_smoke() -> None:
    output = _run_example("examples/cursor-ime/index.py", timeout=1.5)
    assert "Type Korean" in output
    assert ">" in output

def test_suspense_example_smoke() -> None:
    output = _run_example("examples/suspense/index.py", timeout=1.2)
    assert "Loading..." in output or "Hello World" in output


def test_concurrent_suspense_example_smoke() -> None:
    output = _run_example("examples/concurrent-suspense/index.py", timeout=1.2)
    assert "Concurrent Suspense Demo" in output
    assert "Fast data" in output


def test_aria_example_smoke() -> None:
    output = _run_example("examples/aria/index.py", timeout=1.2)
    assert "Press spacebar to toggle the checkbox" in output
    assert "[ ]" in output


@pytest.mark.parametrize(
    ("relative_path", "timeout", "expected"),
    [
        ("examples/box-backgrounds/index.py", 1.5, "Box Background Examples:"),
        ("examples/router/index.py", 1.5, "Home"),
        ("examples/incremental-rendering/index.py", 1.5, "Incremental Rendering"),
        ("examples/jest/index.py", 3.5, "Test Suites:"),
        ("examples/stress-test/index.py", 1.5, "Mode"),
        ("examples/use-focus/index.py", 1.5, "Press Tab to focus next element"),
        ("examples/use-focus-with-id/index.py", 1.5, "Press Tab to focus next element"),
        ("examples/use-stdout/index.py", 1.5, "Terminal dimensions:"),
        ("examples/use-stderr/index.py", 1.5, "Hello World"),
        ("examples/terminal-resize/index.py", 1.5, "Terminal Size"),
        ("examples/table/index.py", 1.5, "Email"),
        ("examples/borders/index.py", 1.5, "single"),
        ("examples/chat/index.py", 1.5, "Enter your message:"),
    ],
)
def test_additional_example_smoke(
    relative_path: str,
    timeout: float,
    expected: str,
) -> None:
    output = _run_example(relative_path, timeout=timeout)
    assert expected in output
