"""
App component for pyinkcli.

Canonical component module matching JS basename.
"""

from __future__ import annotations

from typing import Any, TextIO

from pyinkcli._component_runtime import (
    RenderableNode,
    _Fragment,
    createElement,
    isElement,
    scopeRender,
)
from pyinkcli.components._app_context_runtime import _provide_app_context
from pyinkcli.components.CursorContext import _provide_cursor_context
from pyinkcli.components.ErrorBoundary import ErrorBoundary
from pyinkcli.components.FocusContext import _provide_focus_context
from pyinkcli.components.StderrContext import _provide_stderr
from pyinkcli.components.StdinContext import _provide_stdin
from pyinkcli.components.StdoutContext import _provide_stdout
from pyinkcli.hooks._runtime import useEffect
from pyinkcli.hooks.use_focus import _focus_runtime, focusNext, focusPrev
from pyinkcli.hooks.use_input import useInput
from pyinkcli.hooks.use_stderr import useStderr
from pyinkcli.hooks.use_stdin import useStdin
from pyinkcli.hooks.use_stdout import useStdout


class _CursorContextValue:
    def __init__(self, set_cursor_position: Any | None) -> None:
        self._set_cursor_position = set_cursor_position

    def setCursorPosition(self, position: Any) -> None:
        if callable(self._set_cursor_position):
            self._set_cursor_position(position)


class _FocusContextValue:
    @property
    def active_id(self) -> str | None:
        return _focus_runtime.active_id

    def add(self, id: str, options: dict[str, bool]) -> None:
        _focus_runtime.add(id, auto_focus=options.get("autoFocus", False))

    def remove(self, id: str) -> None:
        _focus_runtime.remove(id)

    def activate(self, id: str) -> None:
        _focus_runtime.activate(id)

    def deactivate(self, id: str) -> None:
        _focus_runtime.deactivate(id)

    def enableFocus(self) -> None:
        _focus_runtime.enable_focus()

    def disableFocus(self) -> None:
        _focus_runtime.disable_focus()

    def focusNext(self) -> None:
        focusNext()

    def focusPrevious(self) -> None:
        focusPrev()

    def focus(self, id: str) -> None:
        _focus_runtime.focus(id)


def App(
    *children: RenderableNode,
    app_context: Any | None = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    exit_on_ctrl_c: bool = True,
    interactive: bool = True,
    debug: bool = False,
    write_to_stdout: Any | None = None,
    write_to_stderr: Any | None = None,
    on_exit: Any | None = None,
    set_cursor_position: Any | None = None,
) -> RenderableNode:
    stdin_handle = useStdin()
    stdout_handle = useStdout()
    stderr_handle = useStderr()
    cursor_context = _CursorContextValue(set_cursor_position)
    focus_context = _FocusContextValue()

    def sync_runtime():
        if stdout_handle is not None:
            bind_stdout = getattr(stdout_handle, "bind_overlay_writer", None)
            if callable(bind_stdout):
                bind_stdout(write_to_stdout)
        if stderr_handle is not None:
            bind_stderr = getattr(stderr_handle, "bind_overlay_writer", None)
            if callable(bind_stderr):
                bind_stderr(write_to_stderr)

        if app_context is not None:
            app_context.stdin = stdin
            app_context.stdout = stdout
            app_context.stderr = stderr
            app_context.exit_on_ctrl_c = exit_on_ctrl_c
            app_context.interactive = interactive
            app_context.write_to_stdout = write_to_stdout
            app_context.write_to_stderr = write_to_stderr
            app_context.set_cursor_position = set_cursor_position
            app_context.on_exit = on_exit
            app_context.on_wait_until_render_flush = getattr(
                app_context.app,
                "wait_until_render_flush",
                None,
            )

        def cleanup():
            stdin_handle.cleanup_runtime_modes()
            if stdout_handle is not None:
                bind_stdout = getattr(stdout_handle, "bind_overlay_writer", None)
                if callable(bind_stdout):
                    bind_stdout(None)
            if stderr_handle is not None:
                bind_stderr = getattr(stderr_handle, "bind_overlay_writer", None)
                if callable(bind_stderr):
                    bind_stderr(None)
            writer = None
            if stdout_handle is not None:
                writer = getattr(stdout_handle, "raw_write", None) or getattr(stdout_handle, "write", None)
            if callable(writer):
                writer("\x1b[?25h")

        return cleanup

    useEffect(sync_runtime, (interactive, stdin, stdout, stderr, set_cursor_position))

    def handle_exit(error_or_result: Any | None = None) -> None:
        stdin_handle.cleanup_runtime_modes()
        if callable(on_exit):
            on_exit(error_or_result)

    def handle_input(input_char, key) -> None:
        if input_char == "\x03" and exit_on_ctrl_c:
            handle_exit()

    useInput(handle_input, is_active=interactive)

    if len(children) == 1:
        body = children[0] if isElement(children[0]) else createElement("ink-text", children[0])
    else:
        body = createElement(_Fragment, *children)

    return scopeRender(
        createElement(
            ErrorBoundary,
            body,
            onError=handle_exit,
        ),
        lambda: _provide_app_context(app_context),
        lambda: _provide_stdin(stdin_handle),
        lambda: _provide_stdout(stdout_handle),
        lambda: _provide_stderr(stderr_handle),
        lambda: _provide_focus_context(focus_context),
        lambda: _provide_cursor_context(cursor_context),
    )


__all__ = ["App"]


App.displayName = "InternalApp"
