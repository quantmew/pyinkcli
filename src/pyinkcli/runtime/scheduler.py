from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable

from .loop_thread import AsyncLoopThread

_PRIORITY_ORDER = {
    "transition": 0,
    "default": 1,
    "discrete": 2,
}


class RenderScheduler:
    def __init__(
        self,
        loop_thread: AsyncLoopThread | None,
        render_callback: Callable[[str], None],
        *,
        max_fps: int = 60,
    ) -> None:
        self._loop_thread = loop_thread
        self._render_callback = render_callback
        self._max_fps = max_fps
        self._pending_handle: asyncio.Handle | None = None
        self._pending_priority: str | None = None
        self._pending_due = 0.0
        self._last_render_at = 0.0
        self._idle = threading.Event()
        self._idle.set()

    def _frame_interval(self) -> float:
        if self._max_fps <= 0:
            return 0.0
        return 1.0 / max(self._max_fps, 1)

    def schedule_render(self, priority: str = "default") -> None:
        if self._loop_thread is None:
            self._render_callback(priority)
            return
        self._idle.clear()
        self._loop_thread.call_soon(self._schedule_on_loop, priority)

    def wait_for_idle(self, timeout: float | None = None) -> bool:
        return self._idle.wait(timeout)

    def _schedule_on_loop(self, priority: str) -> None:
        if self._loop_thread is None:
            self._render_callback(priority)
            return
        now = self._loop_thread.loop.time()
        self._idle.clear()
        if self._pending_priority is None or _PRIORITY_ORDER[priority] > _PRIORITY_ORDER[self._pending_priority]:
            self._pending_priority = priority
        if priority == "discrete":
            due = now
        elif priority == "default":
            due = max(now, self._last_render_at + self._frame_interval())
        else:
            due = max(now, self._last_render_at + self._frame_interval())

        if self._pending_handle is not None and self._pending_due <= due:
            return

        if self._pending_handle is not None:
            self._pending_handle.cancel()

        self._pending_due = due
        delay = max(due - now, 0.0)
        if delay == 0:
            self._pending_handle = self._loop_thread.loop.call_soon(self._flush)
        else:
            self._pending_handle = self._loop_thread.loop.call_later(delay, self._flush)

    def _flush(self) -> None:
        priority = self._pending_priority or "default"
        self._pending_priority = None
        self._pending_due = 0.0
        self._pending_handle = None
        self._render_callback(priority)
        if self._loop_thread is not None:
            self._last_render_at = self._loop_thread.loop.time()
        else:
            self._last_render_at = 0.0
        self._idle.set()
