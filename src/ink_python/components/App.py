"""
App component for ink-python.

Canonical component module matching JS basename.
"""

from __future__ import annotations

from typing import Any, Optional, TextIO

from ink_python._component_runtime import RenderableNode, createElement, isElement
from ink_python.components._app_context_runtime import _get_app_context
from ink_python.hooks._runtime import useEffect
from ink_python.hooks.use_input import useInput


def App(
    *children: RenderableNode,
    stdin: Optional[TextIO] = None,
    stdout: Optional[TextIO] = None,
    stderr: Optional[TextIO] = None,
    exit_on_ctrl_c: bool = True,
    interactive: bool = True,
    debug: bool = False,
    write_to_stdout: Optional[Any] = None,
    write_to_stderr: Optional[Any] = None,
    on_exit: Optional[Any] = None,
) -> RenderableNode:
    app_context = _get_app_context()

    def sync_runtime():
        if app_context is not None:
            app_context.stdin = stdin
            app_context.stdout = stdout
            app_context.stderr = stderr
            app_context.exit_on_ctrl_c = exit_on_ctrl_c
            app_context.interactive = interactive
            app_context.write_to_stdout = write_to_stdout
            app_context.write_to_stderr = write_to_stderr
            app_context.on_exit = on_exit
            app_context.on_wait_until_render_flush = getattr(
                app_context.app,
                "wait_until_render_flush",
                None,
            )

        def cleanup():
            writer = None
            if stdout is not None:
                writer = getattr(stdout, "raw_write", None) or getattr(stdout, "write", None)
            if callable(writer):
                writer("\x1b[?25h")

        return cleanup

    useEffect(sync_runtime, (interactive, stdin, stdout, stderr))

    def handle_input(input_char, key) -> None:
        if input_char == "\x03" and exit_on_ctrl_c and callable(on_exit):
            on_exit()

    useInput(handle_input, is_active=interactive)

    if len(children) == 1:
        return children[0] if isElement(children[0]) else createElement("ink-text", children[0])

    return createElement("ink-root", *children)


__all__ = ["App"]
