"""
App component for ink-python.

The root component that provides context to children.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Union

from ink_python.component import VNode, create_vnode, component
from ink_python.context import (
    provide_accessibility,
    provide_stdin,
    provide_stdout,
    provide_stderr,
)


@component
def App(
    *children: Union[VNode, str, None],
    stdin: Any = None,
    stdout: Any = None,
    stderr: Any = None,
    exit_on_ctrl_c: bool = True,
    interactive: bool = True,
    write_to_stdout: Optional[Callable[[str], None]] = None,
    write_to_stderr: Optional[Callable[[str], None]] = None,
    set_cursor_position: Optional[Callable[[tuple[int, int]], None]] = None,
    on_exit: Optional[Callable[[Any], None]] = None,
    on_wait_until_render_flush: Optional[Callable[[], None]] = None,
    **kwargs: Any,
) -> VNode:
    """
    Root App component.

    Provides context for stdin, stdout, and other app-level concerns.

    Args:
        *children: Child components.
        stdin: Standard input stream.
        stdout: Standard output stream.
        stderr: Standard error stream.
        exit_on_ctrl_c: Whether to exit on Ctrl+C.
        interactive: Whether the app is interactive.
        write_to_stdout: Function to write to stdout.
        write_to_stderr: Function to write to stderr.
        set_cursor_position: Function to set cursor position.
        on_exit: Function to call on exit.
        on_wait_until_render_flush: Function to wait for render flush.
        **kwargs: Additional props.

    Returns:
        A VNode representing the app.
    """
    # For simplicity, we just pass through children
    # In a full implementation, this would set up context providers
    return create_vnode("ink-box", *children, style={"flexDirection": "column"})
