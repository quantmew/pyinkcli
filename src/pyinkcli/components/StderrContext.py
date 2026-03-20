"""
Stderr context split from `context.py`.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, TypedDict


class Props(TypedDict):
    stderr: Any
    write: Any


StderrContext: ContextVar[Any] = ContextVar("stderr_context", default=None)


def _get_stderr() -> Any:
    return StderrContext.get()


@contextmanager
def _provide_stderr(stderr: Any) -> Generator[None, None, None]:
    token = StderrContext.set(stderr)
    try:
        yield
    finally:
        StderrContext.reset(token)


get_stderr = _get_stderr
provide_stderr = _provide_stderr


__all__ = ["StderrContext"]
