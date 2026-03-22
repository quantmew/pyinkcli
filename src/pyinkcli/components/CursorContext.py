from __future__ import annotations

from contextlib import contextmanager

_cursor_context = None


class CursorContext:
    pass


@contextmanager
def _provide_cursor_context(value):
    global _cursor_context
    previous = _cursor_context
    _cursor_context = value
    try:
        yield value
    finally:
        _cursor_context = previous


__all__ = ["CursorContext"]

