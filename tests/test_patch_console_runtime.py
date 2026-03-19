"""Tests for Ink patch_console parity behavior."""

from __future__ import annotations

import sys
from io import StringIO

from pyinkcli import Text, render


class FakeStdout(StringIO):
    def isatty(self) -> bool:
        return False


class FakeTTY(StringIO):
    def isatty(self) -> bool:
        return True


class FakeStdin(StringIO):
    def isatty(self) -> bool:
        return False


def test_patch_console_routes_print_to_non_tty_stdout() -> None:
    stdout = FakeStdout()
    stderr = FakeStdout()
    stdin = FakeStdin()
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    app = render(
        Text("frame"),
        stdout=stdout,
        stderr=stderr,
        stdin=stdin,
        interactive=False,
        patch_console=True,
    )
    try:
        print("hello from print")
        assert "hello from print\n" in stdout.getvalue()
        assert sys.stdout is not original_stdout
        assert sys.stderr is not original_stderr
    finally:
        app.unmount()

    assert sys.stdout is original_stdout
    assert sys.stderr is original_stderr


def test_patch_console_routes_stderr_write_to_non_tty_stderr() -> None:
    stdout = FakeStdout()
    stderr = FakeStdout()
    stdin = FakeStdin()
    app = render(
        Text("frame"),
        stdout=stdout,
        stderr=stderr,
        stdin=stdin,
        interactive=False,
        patch_console=True,
    )
    try:
        sys.stderr.write("problem\n")
        assert stderr.getvalue() == "problem\n"
    finally:
        app.unmount()


def test_patch_console_filters_react_runtime_banner_on_stderr() -> None:
    stdout = FakeStdout()
    stderr = FakeStdout()
    stdin = FakeStdin()
    app = render(
        Text("frame"),
        stdout=stdout,
        stderr=stderr,
        stdin=stdin,
        interactive=False,
        patch_console=True,
    )
    try:
        sys.stderr.write("The above error occurred in the <Example> component\n")
        assert stderr.getvalue() == ""
    finally:
        app.unmount()


def test_patch_console_routes_print_through_tty_overlay_path() -> None:
    stdout = FakeTTY()
    stderr = FakeTTY()
    stdin = FakeTTY()
    app = render(
        Text("frame"),
        stdout=stdout,
        stderr=stderr,
        stdin=stdin,
        interactive=True,
        patch_console=True,
        debug=False,
    )
    try:
        stdout.seek(0)
        stdout.truncate(0)
        print("overlay")
        value = stdout.getvalue()
        assert "overlay\r\n" in value
        assert "frame" in value
    finally:
        app.unmount()


def test_patch_console_is_disabled_in_debug_mode() -> None:
    stdout = FakeStdout()
    stderr = FakeStdout()
    stdin = FakeStdin()
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    app = render(
        Text("frame"),
        stdout=stdout,
        stderr=stderr,
        stdin=stdin,
        debug=True,
        patch_console=True,
    )
    try:
        assert sys.stdout is original_stdout
        assert sys.stderr is original_stderr
    finally:
        app.unmount()
