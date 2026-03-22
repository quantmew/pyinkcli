"""Hook/runtime dispatcher bridge used by the compatibility surface."""

from __future__ import annotations

import importlib
from collections.abc import Callable


def _runtime():
    return importlib.import_module("pyinkcli.hooks._runtime")


def beginComponentRender(fiber_or_instance_id):
    return _runtime()._begin_component_render(fiber_or_instance_id)


def endComponentRender():
    return _runtime()._end_component_render()


def resetHookState() -> None:
    _runtime()._reset_hook_state()


def clearHookState() -> None:
    _runtime()._clear_hook_state()


def setScheduleUpdateCallback(callback):
    _runtime()._set_schedule_update_callback(callback)


def setRerenderCallback(callback):
    _runtime()._set_rerender_callback(callback)


def requestRerender(fiber=None, priority=None) -> None:
    _runtime()._request_rerender(fiber, priority=priority)


def consumePendingRerenderPriority():
    return _runtime()._consume_pending_rerender_priority()


def flushScheduledRerender() -> bool:
    return _runtime()._flush_scheduled_rerender()


def queueAfterCurrentBatch(callback: Callable[[], None]) -> None:
    _runtime()._queue_after_current_batch(callback)


def hasRerenderTarget() -> bool:
    return _runtime()._has_rerender_target()


__all__ = [
    "beginComponentRender",
    "endComponentRender",
    "resetHookState",
    "clearHookState",
    "setScheduleUpdateCallback",
    "setRerenderCallback",
    "requestRerender",
    "consumePendingRerenderPriority",
    "flushScheduledRerender",
    "queueAfterCurrentBatch",
    "hasRerenderTarget",
]
