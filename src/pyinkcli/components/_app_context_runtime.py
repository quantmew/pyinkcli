"""Internal runtime helpers for AppContext."""

from __future__ import annotations

from collections.abc import Callable, Generator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any


class Props:
    def __init__(self, app: Any = None):
        self.app = app
        self.stdin: Any = None
        self.stdout: Any = None
        self.stderr: Any = None
        self.exit_on_ctrl_c: bool = True
        self.interactive: bool = True
        self.write_to_stdout: Callable[[str], None] | None = None
        self.write_to_stderr: Callable[[str], None] | None = None
        self.set_cursor_position: Callable[[tuple[int, int] | None], None] | None = None
        self.schedule_transition: Callable[[Callable[[], None], Callable[[bool], None] | None, float], None] | None = None
        self.on_exit: Callable[[Any], None] | None = None
        self.on_wait_until_render_flush: Callable[[], None] | None = None


AppContext: ContextVar[Props | None] = ContextVar("app_context", default=None)


def _get_app_context() -> Props | None:
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
