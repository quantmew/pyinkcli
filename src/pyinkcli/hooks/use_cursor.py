"""useCursor hook for pyinkcli."""

from __future__ import annotations

from typing import Mapping, Optional, Union

from pyinkcli.components._app_context_runtime import _get_app_context
from pyinkcli.components.CursorContext import _get_cursor_context
from pyinkcli.hooks._runtime import Ref, useEffect, useRef
from pyinkcli.hooks.use_stdout import useStdout
from pyinkcli.utils.ansi_escapes import cursor_show, cursor_hide


class _CursorHandle:
    """Object-shaped cursor control handle."""

    def __init__(self, position_ref: Ref[tuple[int, int]]):
        self._position_ref = position_ref

    def setCursorPosition(
        self,
        position: Optional[Union[tuple[int, int], Mapping[str, int]]],
    ) -> None:
        if position is None:
            self._position_ref.current = None
            return

        if isinstance(position, Mapping):
            self._position_ref.current = (
                max(0, int(position.get("x", 0))),
                max(0, int(position.get("y", 0))),
            )
            return

        self._position_ref.current = (
            max(0, int(position[0])),
            max(0, int(position[1])),
        )


def useCursor(
    visible: Optional[bool] = None,
    *,
    enabled: bool = True,
) -> _CursorHandle:
    """
    A React hook that controls cursor visibility and position.

    Args:
        visible: Whether the terminal cursor should be visible.
            Pass `None` to only manage cursor position.

    Example:
        >>> useCursor(False)  # Hide cursor
        >>> cursor = useCursor()
        >>> cursor.setCursorPosition((3, 1))
    """
    stdout = useStdout()
    app_context = _get_app_context()
    cursor_context = _get_cursor_context()
    position_ref = useRef(None)

    def apply_cursor_visibility():
        if visible is None or not enabled:
            return None

        writer = getattr(stdout, "raw_write", stdout.write)
        if visible:
            writer(cursor_show())
        else:
            writer(cursor_hide())

        def cleanup():
            writer(cursor_show())

        return cleanup

    def sync_cursor_position():
        set_cursor_position = None
        if cursor_context is not None:
            set_cursor_position = getattr(cursor_context, "setCursorPosition", None)
        elif app_context is not None:
            set_cursor_position = app_context.set_cursor_position

        if set_cursor_position is None:
            return None

        set_cursor_position(position_ref.current if enabled else None)

        def cleanup():
            if set_cursor_position is not None:
                set_cursor_position(None)

        return cleanup

    useEffect(apply_cursor_visibility, (visible, enabled))
    useEffect(sync_cursor_position)
    return _CursorHandle(position_ref)
