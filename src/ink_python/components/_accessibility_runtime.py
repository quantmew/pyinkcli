"""Internal runtime helpers for accessibility context."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Generator


accessibilityContext: ContextVar[dict[str, bool]] = ContextVar(
    "accessibility_context",
    default={"isScreenReaderEnabled": False},
)


def _is_screen_reader_enabled() -> bool:
    return accessibilityContext.get().get("isScreenReaderEnabled", False)


@contextmanager
def _provide_accessibility(enabled: bool) -> Generator[None, None, None]:
    token = accessibilityContext.set({"isScreenReaderEnabled": enabled})
    try:
        yield
    finally:
        accessibilityContext.reset(token)
