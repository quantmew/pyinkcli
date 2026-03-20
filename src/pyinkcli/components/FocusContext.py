"""Focus context matching JS `components/FocusContext.ts`."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Protocol


class Props(Protocol):
    active_id: Any

    def add(self, id: str, options: dict[str, bool]) -> None: ...
    def remove(self, id: str) -> None: ...
    def activate(self, id: str) -> None: ...
    def deactivate(self, id: str) -> None: ...
    def enableFocus(self) -> None: ...
    def disableFocus(self) -> None: ...
    def focusNext(self) -> None: ...
    def focusPrevious(self) -> None: ...
    def focus(self, id: str) -> None: ...


FocusContext: ContextVar[Any] = ContextVar("focus_context", default=None)


def _get_focus_context() -> Any:
    return FocusContext.get()


@contextmanager
def _provide_focus_context(value: Any) -> Generator[None, None, None]:
    token = FocusContext.set(value)
    try:
        yield
    finally:
        FocusContext.reset(token)


__all__ = ["FocusContext"]
