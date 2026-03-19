"""Tests for user-facing stdout/stderr write sanitization."""

from io import StringIO

from pyinkcli import Text, render
from pyinkcli import ink as ink_module
from pyinkcli.hooks.use_stderr import _StderrHandle
from pyinkcli.hooks.use_stdout import _StdoutHandle


class FakeStdout(StringIO):
    def isatty(self) -> bool:
        return False


class FakeStderr(StringIO):
    def isatty(self) -> bool:
        return False


class FakeStdin(StringIO):
    def isatty(self) -> bool:
        return False


def test_stdout_handle_write_sanitizes_control_sequences():
    stream = FakeStdout()
    handle = _StdoutHandle(stream)

    handle.write("A\x1b[2JB")

    assert stream.getvalue() == "AB"


def test_stdout_handle_write_uses_overlay_writer_when_bound():
    stream = FakeStdout()
    writes: list[str] = []
    handle = _StdoutHandle(stream)
    handle.bind_overlay_writer(writes.append)

    handle.write("A\x1b[2JB\n")

    assert writes == ["AB\n"]
    assert stream.getvalue() == ""


def test_stdout_handle_raw_write_preserves_control_sequences():
    stream = FakeStdout()
    handle = _StdoutHandle(stream)

    handle.raw_write("\x1b[?25l")

    assert stream.getvalue() == "\x1b[?25l"


def test_stderr_handle_write_sanitizes_control_sequences():
    stream = FakeStderr()
    handle = _StderrHandle(stream)

    handle.write("A\x1b[2JB")

    assert stream.getvalue() == "AB"


def test_stderr_handle_write_uses_overlay_writer_when_bound():
    stream = FakeStderr()
    writes: list[str] = []
    handle = _StderrHandle(stream)
    handle.bind_overlay_writer(writes.append)

    handle.write("A\x1b[2JB\n")

    assert writes == ["AB\n"]
    assert stream.getvalue() == ""


def test_ink_write_to_stdout_sanitizes_user_output():
    stdout = FakeStdout()
    stdin = FakeStdin()

    app = render(Text("hello"), stdout=stdout, stdin=stdin, debug=True)
    stdout.seek(0)
    stdout.truncate(0)

    app._write_to_stdout("A\x1b[2JB")

    assert "\x1b[2J" not in stdout.getvalue()
    assert stdout.getvalue().startswith("AB")
    app.unmount()


def test_ink_write_to_stderr_sanitizes_user_output():
    stdout = FakeStdout()
    stderr = FakeStderr()
    stdin = FakeStdin()

    app = render(Text("hello"), stdout=stdout, stderr=stderr, stdin=stdin, debug=True)
    app._write_to_stderr("A\x1b[2JB")

    assert stderr.getvalue() == "AB"
    app.unmount()


def test_debug_render_path_sanitizes_render_result_output(monkeypatch):
    stdout = FakeStdout()
    stdin = FakeStdin()

    original_render_dom = ink_module.render_dom

    def fake_render_dom(node, is_screen_reader_enabled):
        return ink_module.RenderResult(
            output="A\x1b[2JB",
            output_height=1,
            static_output="S\x1b[2JT\n",
        )

    monkeypatch.setattr(ink_module, "render_dom", fake_render_dom)
    try:
        app = render(Text("hello"), stdout=stdout, stdin=stdin, debug=True)
        assert "\x1b[2J" not in stdout.getvalue()
        assert stdout.getvalue() == "ST\nAB"
        app.unmount()
    finally:
        monkeypatch.setattr(ink_module, "render_dom", original_render_dom)
