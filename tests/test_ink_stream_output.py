"""Tests for direct Ink stream writes that bypass log-update."""

from __future__ import annotations

from io import StringIO

from ink_python import Text, render
from ink_python.ink import Ink, Options


class FakeTTY(StringIO):
    def isatty(self) -> bool:
        return True


def test_ink_prepare_stream_payload_normalizes_newlines_for_tty() -> None:
    stdout = FakeTTY()
    stdin = FakeTTY()
    ink = Ink(Options(stdout=stdout, stdin=stdin, stderr=stdout, interactive=True))
    try:
        assert ink._prepare_stream_payload(stdout, "a\nb\n") == "a\r\nb\r\n"
        assert ink._prepare_stream_payload(stdout, "\x1b[?25l") == "\x1b[?25l"
    finally:
        ink.unmount()


def test_ink_write_stream_preserves_non_tty_newlines() -> None:
    stdout = StringIO()
    stdin = StringIO()
    ink = Ink(Options(stdout=stdout, stdin=stdin, stderr=stdout, interactive=False))
    try:
        ink._write_stream(stdout, "a\nb\n")
        assert stdout.getvalue() == "a\nb\n"
    finally:
        ink.unmount()


def test_ink_overlay_stdout_normalizes_newlines_for_tty_debug_path() -> None:
    stdout = FakeTTY()
    stderr = FakeTTY()
    stdin = FakeTTY()
    app = render(Text("frame"), stdout=stdout, stderr=stderr, stdin=stdin, interactive=True, debug=True)
    try:
        stdout.seek(0)
        stdout.truncate(0)
        app._write_to_stdout("top\nline")
        assert stdout.getvalue() == "top\r\nlineframe"
    finally:
        app.unmount()


def test_ink_overlay_stderr_normalizes_newlines_for_tty_debug_path() -> None:
    stdout = FakeTTY()
    stderr = FakeTTY()
    stdin = FakeTTY()
    app = render(Text("frame"), stdout=stdout, stderr=stderr, stdin=stdin, interactive=True, debug=True)
    try:
        app._write_to_stderr("err\nline")
        assert stderr.getvalue() == "err\r\nline"
    finally:
        app.unmount()


def test_ink_alternate_screen_sequences_remain_escape_only() -> None:
    stdout = FakeTTY()
    stdin = FakeTTY()
    ink = Ink(Options(stdout=stdout, stdin=stdin, stderr=stdout, interactive=True, alternate_screen=True))
    try:
        prefix = stdout.getvalue()
        assert "\x1b[?1049h" in prefix
        assert "\x1b[?25l" in prefix
        assert "\r\n" not in prefix
    finally:
        ink.unmount()
