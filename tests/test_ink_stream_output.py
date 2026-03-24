"""Tests for direct Ink stream writes that bypass log-update."""

from __future__ import annotations

from io import StringIO

from pyinkcli import Text, render, useWindowSize
from pyinkcli.ink import Ink, Options
from pyinkcli.runtime.output_driver import OutputDriver
from pyinkcli.utils.ansi_escapes import clear_terminal


class FakeTTY(StringIO):
    def isatty(self) -> bool:
        return True


class ResizableTTY(FakeTTY):
    def __init__(self, columns: int, rows: int):
        super().__init__()
        self.columns = columns
        self.rows = rows


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


def test_use_window_size_updates_after_resize_rerender() -> None:
    stdout = ResizableTTY(columns=80, rows=24)
    stderr = ResizableTTY(columns=80, rows=24)
    stdin = ResizableTTY(columns=80, rows=24)

    def Example():
        columns, rows = useWindowSize()
        return Text(f"{columns}x{rows}")

    app = render(
        Example,
        stdout=stdout,
        stderr=stderr,
        stdin=stdin,
        interactive=True,
        patch_console=False,
    )
    try:
        assert "80x24" in stdout.getvalue()

        stdout.seek(0)
        stdout.truncate(0)
        stdout.columns = 100
        stdout.rows = 40
        app._handle_resize()
        app.wait_until_render_flush(timeout=1.0)

        assert "100x40" in stdout.getvalue()
    finally:
        app.unmount()


def test_resize_rerender_bypasses_normal_throttle() -> None:
    stdout = ResizableTTY(columns=80, rows=24)
    stderr = ResizableTTY(columns=80, rows=24)
    stdin = ResizableTTY(columns=80, rows=24)

    def Example():
        columns, rows = useWindowSize()
        return Text(f"{columns}x{rows}")

    app = render(
        Example,
        stdout=stdout,
        stderr=stderr,
        stdin=stdin,
        interactive=True,
        patch_console=False,
        max_fps=1,
    )
    try:
        assert "80x24" in stdout.getvalue()

        stdout.seek(0)
        stdout.truncate(0)
        stdout.columns = 60
        stdout.rows = 24
        app._handle_resize()
        app.wait_until_render_flush(timeout=0.3)

        assert "60x24" in stdout.getvalue()
    finally:
        app.unmount()


def test_width_decrease_clears_last_output_before_resize_rerender() -> None:
    stdout = ResizableTTY(columns=100, rows=24)
    stderr = ResizableTTY(columns=100, rows=24)
    stdin = ResizableTTY(columns=100, rows=24)

    def Example():
        return Text("resize me")

    app = render(
        Example,
        stdout=stdout,
        stderr=stderr,
        stdin=stdin,
        interactive=True,
        patch_console=False,
    )
    try:
        assert app._output_driver.last_output == "resize me"
        stdout.columns = 80
        stdout.rows = 24
        app._handle_resize()
        app.wait_until_render_flush(timeout=1.0)

        assert app._last_terminal_width == 80
        assert app._output_driver.last_output == "resize me"
    finally:
        app.unmount()


def test_reset_rendered_frame_can_preserve_height() -> None:
    stdout = ResizableTTY(columns=100, rows=24)
    stderr = ResizableTTY(columns=100, rows=24)
    stdin = ResizableTTY(columns=100, rows=24)

    app = render(
        Text("frame"),
        stdout=stdout,
        stderr=stderr,
        stdin=stdin,
        interactive=True,
        patch_console=False,
    )
    try:
        app._output_driver.last_output_height = 7
        app._reset_rendered_frame(preserve_height=True)
        assert app._output_driver.last_output == ""
        assert app._output_driver.last_output_to_render == ""
        assert app._output_driver.last_output_height == 7
    finally:
        app.unmount()


def test_output_driver_full_clears_incremental_overflowing_frames() -> None:
    stdout = ResizableTTY(columns=20, rows=3)
    driver = OutputDriver(stdout, interactive=True, incremental=True)

    first = "line1\nline2\nline3\nline4"
    second = "line1\nline2\nline3\nchanged"

    assert driver.render_frame(first) is True
    first_payload = stdout.getvalue()
    assert clear_terminal() not in first_payload

    stdout.seek(0)
    stdout.truncate(0)

    assert driver.render_frame(second) is True
    second_payload = stdout.getvalue()

    assert clear_terminal() in second_payload


def test_output_driver_normalizes_newlines_in_full_clear_path_for_tty() -> None:
    stdout = ResizableTTY(columns=20, rows=3)
    driver = OutputDriver(stdout, interactive=True, incremental=True)

    first = "line1\nline2\nline3\nline4"
    second = "head\nbody\nfoot\nlast"

    driver.render_frame(first)
    stdout.seek(0)
    stdout.truncate(0)

    driver.render_frame(second)
    payload = stdout.getvalue()

    assert clear_terminal() in payload
    assert "head\r\nbody\r\nfoot\r\nlast" in payload
