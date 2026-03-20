"""Internal runtime helpers for accessibility context."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar

accessibilityContext: ContextVar[dict[str, bool] | None] = ContextVar(
    "accessibility_context",
    default=None,
)


def _is_screen_reader_enabled() -> bool:
    context = accessibilityContext.get()
    return context.get("isScreenReaderEnabled", False) if context is not None else False


@contextmanager
def _provide_accessibility(enabled: bool) -> Generator[None, None, None]:
    token = accessibilityContext.set({"isScreenReaderEnabled": enabled})
    try:
        yield
    finally:
        accessibilityContext.reset(token)
