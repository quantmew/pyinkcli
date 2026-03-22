from __future__ import annotations

from contextlib import contextmanager

_focus_context = None


class FocusContext:
    pass


@contextmanager
def _provide_focus_context(value):
    global _focus_context
    previous = _focus_context
    _focus_context = value
    try:
        yield value
    finally:
        _focus_context = previous


__all__ = ["FocusContext"]

