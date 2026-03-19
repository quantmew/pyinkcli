"""Cursor context matching JS `components/CursorContext.ts`."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Generator, Protocol


class Props(Protocol):
    def setCursorPosition(self, position: Any) -> None: ...


CursorContext: ContextVar[Any] = ContextVar("cursor_context", default=None)


def _get_cursor_context() -> Any:
    return CursorContext.get()


@contextmanager
def _provide_cursor_context(value: Any) -> Generator[None, None, None]:
    token = CursorContext.set(value)
    try:
        yield
    finally:
        CursorContext.reset(token)


__all__ = ["CursorContext", "Props"]
