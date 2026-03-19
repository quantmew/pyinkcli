"""
Stdout context split from `context.py`.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Generator, TypedDict


class Props(TypedDict):
    stdout: Any
    write: Any


StdoutContext: ContextVar[Any] = ContextVar("stdout_context", default=None)


def _get_stdout() -> Any:
    return StdoutContext.get()


@contextmanager
def _provide_stdout(stdout: Any) -> Generator[None, None, None]:
    token = StdoutContext.set(stdout)
    try:
        yield
    finally:
        StdoutContext.reset(token)


get_stdout = _get_stdout
provide_stdout = _provide_stdout


__all__ = ["StdoutContext"]
