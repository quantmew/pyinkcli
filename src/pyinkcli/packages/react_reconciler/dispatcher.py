"""Compatibility bridge onto the internal hooks runtime."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pyinkcli.hooks import _runtime as _runtime


def beginComponentRender(fiber_or_instance_id):
    return _runtime._begin_component_render(fiber_or_instance_id)


def endComponentRender():
    return _runtime._end_component_render()


def resetHookState() -> None:
    _runtime._reset_hook_state()


def clearHookState() -> None:
    _runtime._clear_hook_state()


def finishHookState(
    *,
    defer_passive_effects_to_commit: bool = False,
    defer_non_passive_hook_effects_to_commit: bool = False,
) -> None:
    _runtime._finish_hook_state(
        defer_passive_effects_to_commit=defer_passive_effects_to_commit,
        defer_non_passive_hook_effects_to_commit=defer_non_passive_hook_effects_to_commit,
    )


def setScheduleUpdateCallback(
    callback: Callable[[Any, int], None] | None,
) -> None:
    _runtime._set_schedule_update_callback(callback)


def setRerenderCallback(callback: Callable[[], None] | None) -> None:
    _runtime._set_rerender_callback(callback)


def consumePendingRerenderPriority() -> str | None:
    return _runtime._consume_pending_rerender_priority()


def requestRerender(
    fiber: Any | None = None,
    *,
    priority: int | None = None,
) -> None:
    _runtime._request_rerender(fiber, priority=priority)


def flushScheduledRerender() -> bool:
    return _runtime._flush_scheduled_rerender()


def hasRerenderTarget() -> bool:
    return _runtime._has_rerender_target()


def queueAfterCurrentBatch(callback: Callable[[], None]) -> None:
    _runtime._queue_after_current_batch(callback)


def batchedUpdates(callback: Callable[[], Any]) -> Any:
    return _runtime._batched_updates_runtime(callback)


def discreteUpdates(callback: Callable[[], Any]) -> Any:
    return _runtime._discrete_updates_runtime(callback)


__all__ = [
    "beginComponentRender",
    "endComponentRender",
    "resetHookState",
    "clearHookState",
    "finishHookState",
    "setScheduleUpdateCallback",
    "setRerenderCallback",
    "consumePendingRerenderPriority",
    "requestRerender",
    "flushScheduledRerender",
    "hasRerenderTarget",
    "queueAfterCurrentBatch",
    "batchedUpdates",
    "discreteUpdates",
]

