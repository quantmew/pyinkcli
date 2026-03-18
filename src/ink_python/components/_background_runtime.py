"""Internal runtime helpers for background context."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Generator, Optional


BackgroundColor = Optional[str]

backgroundContext: ContextVar[BackgroundColor] = ContextVar(
    "background_context",
    default=None,
)


def _get_background_color() -> BackgroundColor:
    return backgroundContext.get()


@contextmanager
def _provide_background_color(color: BackgroundColor) -> Generator[None, None, None]:
    token = backgroundContext.set(color)
    try:
        yield
    finally:
        backgroundContext.reset(token)
