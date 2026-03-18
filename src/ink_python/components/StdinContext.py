"""
Stdin context split from `context.py`.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Generator, TypedDict


class PublicProps(TypedDict):
    stdin: Any
    setRawMode: Any
    isRawModeSupported: bool


class Props(PublicProps, total=False):
    setBracketedPasteMode: Any
    internal_exitOnCtrlC: bool
    internal_eventEmitter: Any


StdinContext: ContextVar[Any] = ContextVar("stdin_context", default=None)


def _get_stdin() -> Any:
    return StdinContext.get()


@contextmanager
def _provide_stdin(stdin: Any) -> Generator[None, None, None]:
    token = StdinContext.set(stdin)
    try:
        yield
    finally:
        StdinContext.reset(token)


get_stdin = _get_stdin
provide_stdin = _provide_stdin


__all__ = ["StdinContext"]
