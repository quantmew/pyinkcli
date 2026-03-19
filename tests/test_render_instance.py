"""Tests for render instance lifecycle helpers."""

from io import StringIO

from pyinkcli import Text, render, useApp


class FakeStdout(StringIO):
    def isatty(self) -> bool:
        return False


class FakeStdin(StringIO):
    def isatty(self) -> bool:
        return False


def test_wait_until_render_flush_returns_after_render():
    stdout = FakeStdout()
    stdin = FakeStdin()

    app = render(Text("hello"), stdout=stdout, stdin=stdin)
    app.wait_until_render_flush(timeout=0.1)

    app.unmount()


def test_use_app_handle_exposes_wait_until_render_flush():
    stdout = FakeStdout()
    stdin = FakeStdin()

    app = render(Text("hello"), stdout=stdout, stdin=stdin)
    handle = useApp()
    handle.wait_until_render_flush(timeout=0.1)

    app.unmount()
