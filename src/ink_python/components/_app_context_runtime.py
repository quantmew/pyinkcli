"""Internal runtime helpers for AppContext."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Callable, Generator, Optional


class Props:
    def __init__(self, app: Any = None):
        self.app = app
        self.stdin: Any = None
        self.stdout: Any = None
        self.stderr: Any = None
        self.exit_on_ctrl_c: bool = True
        self.interactive: bool = True
        self.write_to_stdout: Optional[Callable[[str], None]] = None
        self.write_to_stderr: Optional[Callable[[str], None]] = None
        self.set_cursor_position: Optional[Callable[[Optional[tuple[int, int]]], None]] = None
        self.schedule_transition: Optional[
            Callable[[Callable[[], None], Optional[Callable[[bool], None]], float], None]
        ] = None
        self.on_exit: Optional[Callable[[Any], None]] = None
        self.on_wait_until_render_flush: Optional[Callable[[], None]] = None


AppContext: ContextVar[Optional[Props]] = ContextVar("app_context", default=None)


def _get_app_context() -> Optional[Props]:
    return AppContext.get()


def _set_app_context(app: Props) -> None:
    AppContext.set(app)


@contextmanager
def _provide_app_context(app: Props) -> Generator[None, None, None]:
    token = AppContext.set(app)
    try:
        yield
    finally:
        AppContext.reset(token)
