from __future__ import annotations

from types import SimpleNamespace

from ..components import CursorContext as cursor_context_module
from .use_app import useApp


def useCursor():
    context = cursor_context_module._cursor_context
    if context is not None:
        return SimpleNamespace(
            setCursorPosition=lambda position: context.setCursorPosition((position["x"], position["y"]))
        )

    def set_cursor_position(position):
        app = useApp()
        if app is None:
            return
        x = max(int(position["x"]), 0)
        y = max(int(position["y"]), 0)
        app._set_cursor_position((x, y))

    return SimpleNamespace(setCursorPosition=set_cursor_position)


__all__ = ["useCursor"]
