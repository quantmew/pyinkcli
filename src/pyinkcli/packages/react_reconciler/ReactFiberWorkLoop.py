"""Work-loop helpers aligned with ReactFiberWorkLoop responsibilities."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pyinkcli.packages.react_reconciler.ReactEventPriorities import (
    DefaultEventPriority,
    DiscreteEventPriority,
    NoEventPriority,
    TransitionEventPriority,
    UpdatePriority,
    higherEventPriority,
)
from pyinkcli.packages.react_reconciler.ReactSharedInternals import shared_internals

if TYPE_CHECKING:
    from pyinkcli.packages.react_reconciler.ReactFiberRoot import ReconcilerContainer
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler


NoContext = 0
BatchedContext = 1 << 0
RenderContext = 1 << 1
CommitContext = 1 << 2

executionContext = NoContext


def priorityRank(priority: UpdatePriority) -> int:
    if priority == NoEventPriority:
        return 0
    return 1000 - priority


def laneToMask(lane: UpdatePriority) -> int:
    if lane == DiscreteEventPriority:
        return 1 << 0
    if lane == DefaultEventPriority:
        return 1 << 1
    if lane == TransitionEventPriority:
        return 1 << 2
    return 1 << 3


def mergeLanes(a: int, b: int) -> int:
    return a | b


def getHighestPriorityLane(lanes: int) -> UpdatePriority:
    if lanes & laneToMask(DiscreteEventPriority):
        return DiscreteEventPriority
    if lanes & laneToMask(DefaultEventPriority):
        return DefaultEventPriority
    if lanes & laneToMask(TransitionEventPriority):
        return TransitionEventPriority
    if lanes != NoEventPriority:
        return max(DefaultEventPriority, lanes)
    return NoEventPriority


def removeLanes(lanes: int, lane: UpdatePriority) -> int:
    return lanes & ~laneToMask(lane)


def requestUpdateLane(_fiber: object | None = None) -> UpdatePriority:
    if shared_internals.current_transition is not None:
        return TransitionEventPriority
    current_priority = shared_internals.current_update_priority
    if current_priority != NoEventPriority:
        return current_priority
    return DefaultEventPriority


def markRootUpdated(container: ReconcilerContainer, lane: UpdatePriority) -> None:
    container.pending_lanes = mergeLanes(container.pending_lanes, laneToMask(lane))
    container.callback_priority = higherEventPriority(
        container.callback_priority,
        lane,
    )


def markRootSuspended(container: ReconcilerContainer, lane: UpdatePriority) -> None:
    lane_mask = laneToMask(lane)
    container.suspended_lanes = mergeLanes(container.suspended_lanes, lane_mask)
    container.pinged_lanes = removeLanes(container.pinged_lanes, lane)


def markRootPinged(container: ReconcilerContainer, lane: UpdatePriority) -> None:
    lane_mask = laneToMask(lane)
    if container.suspended_lanes & lane_mask:
        container.pinged_lanes = mergeLanes(container.pinged_lanes, lane_mask)
    container.pending_lanes = mergeLanes(container.pending_lanes, lane_mask)
    container.callback_priority = higherEventPriority(container.callback_priority, lane)


def scheduleUpdateOnFiber(
    reconciler: _Reconciler,
    container: ReconcilerContainer,
    lane: UpdatePriority,
) -> None:
    markRootUpdated(container, lane)
    requestRerender(reconciler, container, priority=lane)


def requestRerender(
    reconciler: _Reconciler,
    container: ReconcilerContainer,
    *,
    priority: UpdatePriority,
) -> None:
    host_config = reconciler._host_config
    if host_config is None:
        return

    with container.lock:
        container.update_requested = True
        container.pending_work_version += 1
        markRootPinged(container, priority)
        container.pending_update_priority = container.callback_priority
        if container.update_running:
            return
        container.update_running = True

    try:
        while True:
            with container.lock:
                current_component = host_config.get_current_component()
                if not container.update_requested or current_component is None:
                    container.update_running = False
                    return
                container.update_requested = False
                next_lane = getHighestPriorityLane(container.pending_lanes)
                container.current_update_priority = next_lane or DefaultEventPriority
                container.pending_lanes = removeLanes(
                    container.pending_lanes,
                    container.current_update_priority,
                )
                container.callback_priority = getHighestPriorityLane(container.pending_lanes)
                container.pending_update_priority = container.callback_priority

            previous_render_priority = shared_internals.current_render_priority
            shared_internals.current_render_priority = container.current_update_priority
            completed = host_config.perform_render(
                current_component,
                container.current_update_priority,
            )
            if not completed:
                with container.lock:
                    container.pending_lanes = mergeLanes(
                        container.pending_lanes,
                        laneToMask(container.current_update_priority),
                    )
                    container.callback_priority = getHighestPriorityLane(container.pending_lanes)
                    container.pending_update_priority = container.callback_priority
                    container.update_requested = True
                    container.update_running = False
                host_config.schedule_resume(container.current_update_priority)
                return
            shared_internals.current_render_priority = previous_render_priority
            with container.lock:
                if getattr(reconciler, "_render_suspended", False):
                    markRootSuspended(container, container.current_update_priority)
                else:
                    container.suspended_lanes = removeLanes(
                        container.suspended_lanes,
                        container.current_update_priority,
                    )
                    container.pinged_lanes = removeLanes(
                        container.pinged_lanes,
                        container.current_update_priority,
                    )
                has_higher_priority_pending = (
                    container.pending_lanes != NoEventPriority
                    and priorityRank(getHighestPriorityLane(container.pending_lanes))
                    > priorityRank(container.current_update_priority)
                )
            if (
                container.current_update_priority > DiscreteEventPriority
                and not has_higher_priority_pending
            ):
                host_config.wait_for_render_flush(1.0)
    finally:
        with container.lock:
            container.update_running = False
            container.finished_lanes = mergeLanes(
                container.finished_lanes,
                laneToMask(container.current_update_priority),
            )
            container.current_update_priority = NoEventPriority


def dispatchCommitRender(
    reconciler: _Reconciler,
    container: ReconcilerContainer,
) -> None:
    reconciler._request_host_render(container.current_update_priority, immediate=False)


def batchedUpdates(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    global executionContext
    from pyinkcli.hooks._runtime import _batched_updates_runtime

    previous_context = executionContext
    executionContext |= BatchedContext
    try:
        return _batched_updates_runtime(lambda: fn(*args, **kwargs))
    finally:
        executionContext = previous_context


def discreteUpdates(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    global executionContext
    previous_context = executionContext
    previous_priority = shared_internals.current_update_priority
    executionContext |= BatchedContext
    shared_internals.current_update_priority = DiscreteEventPriority
    try:
        return fn(*args, **kwargs)
    finally:
        shared_internals.current_update_priority = previous_priority
        executionContext = previous_context


def flushSyncFromReconciler(fn: Callable[[], Any] | None = None) -> Any:
    global executionContext
    from pyinkcli.hooks._runtime import _flush_scheduled_rerender

    previous_context = executionContext
    previous_priority = shared_internals.current_update_priority
    executionContext |= BatchedContext
    shared_internals.current_update_priority = DiscreteEventPriority
    try:
        result = fn() if fn is not None else None
    finally:
        shared_internals.current_update_priority = previous_priority
        executionContext = previous_context
    _flush_scheduled_rerender()
    return result


__all__ = [
    "BatchedContext",
    "CommitContext",
    "NoContext",
    "RenderContext",
    "batchedUpdates",
    "dispatchCommitRender",
    "discreteUpdates",
    "executionContext",
    "flushSyncFromReconciler",
    "getHighestPriorityLane",
    "laneToMask",
    "markRootUpdated",
    "markRootPinged",
    "markRootSuspended",
    "mergeLanes",
    "priorityRank",
    "removeLanes",
    "requestUpdateLane",
    "requestRerender",
    "scheduleUpdateOnFiber",
]
