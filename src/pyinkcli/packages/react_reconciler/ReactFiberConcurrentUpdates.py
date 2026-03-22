"""Minimal concurrent update queue helpers aligned with ReactFiberConcurrentUpdates."""

from __future__ import annotations

from typing import Any

from pyinkcli.packages.react_reconciler.ReactFiberLane import (
    Lane,
    NoLane,
    NoLanes,
    markRootUpdated,
    mergeLanes,
)
from pyinkcli.packages.react_reconciler.ReactFiberRootScheduler import ensureRootIsScheduled

concurrentQueues: list[tuple[Any, Any, Any, Lane]] = []
concurrentlyUpdatedLanes: int = NoLanes


def markFiberUpdated(fiber: Any, lane: Lane) -> None:
    if fiber is None or lane == NoLane:
        return
    fiber_lanes = getattr(fiber, "lanes", NoLanes)
    setattr(fiber, "lanes", mergeLanes(fiber_lanes, lane))
    alternate = getattr(fiber, "alternate", None)
    if alternate is not None:
        alternate_lanes = getattr(alternate, "lanes", NoLanes)
        setattr(alternate, "lanes", mergeLanes(alternate_lanes, lane))


def finishQueueingConcurrentUpdates() -> None:
    global concurrentQueues, concurrentlyUpdatedLanes
    queued = concurrentQueues
    concurrentQueues = []
    concurrentlyUpdatedLanes = NoLanes
    for fiber, queue, update, lane in queued:
        if queue is not None and update is not None:
            pending = getattr(queue, "pending", None)
            if pending is None:
                update["next"] = update
            else:
                update["next"] = pending["next"]
                pending["next"] = update
            queue.pending = update
        if lane != NoLane:
            markUpdateLaneFromFiberToRoot(fiber, update, lane)


def getConcurrentlyUpdatedLanes() -> int:
    return concurrentlyUpdatedLanes


def enqueueUpdate(
    fiber: Any,
    queue: Any,
    update: Any,
    lane: Lane,
) -> None:
    global concurrentlyUpdatedLanes
    concurrentQueues.append((fiber, queue, update, lane))
    concurrentlyUpdatedLanes = mergeLanes(concurrentlyUpdatedLanes, lane)
    markFiberUpdated(fiber, lane)


def getRootForUpdatedFiber(sourceFiber: Any) -> Any | None:
    current = sourceFiber
    while current is not None:
        if getattr(current, "tag", None) == 3 or hasattr(current, "container"):
            return current
        current = getattr(current, "return_fiber", None)
    return None


def markUpdateLaneFromFiberToRoot(
    sourceFiber: Any,
    update: Any,
    lane: Lane,
) -> Any | None:
    del update
    current = sourceFiber
    root = None
    while current is not None:
        child_lanes = getattr(current, "child_lanes", NoLanes)
        setattr(current, "child_lanes", mergeLanes(child_lanes, lane))
        alternate = getattr(current, "alternate", None)
        if alternate is not None:
            alternate_child_lanes = getattr(alternate, "child_lanes", NoLanes)
            setattr(alternate, "child_lanes", mergeLanes(alternate_child_lanes, lane))
        if getattr(current, "tag", None) == 3 or hasattr(current, "container"):
            root = current
            break
        current = getattr(current, "return_fiber", None)
    if root is None:
        return None
    markRootUpdated(root, lane)
    ensureRootIsScheduled(root)
    return root


def enqueueConcurrentHookUpdate(
    fiber: Any,
    queue: Any,
    update: Any,
    lane: Lane,
) -> Any | None:
    enqueueUpdate(fiber, queue, update, lane)
    return getRootForUpdatedFiber(fiber)


def enqueueConcurrentHookUpdateAndEagerlyBailout(
    fiber: Any,
    queue: Any,
    update: Any,
) -> None:
    enqueueUpdate(fiber, queue, update, NoLane)
    finishQueueingConcurrentUpdates()


def enqueueConcurrentClassUpdate(
    fiber: Any,
    queue: Any,
    update: Any,
    lane: Lane,
) -> Any | None:
    enqueueUpdate(fiber, queue, update, lane)
    return getRootForUpdatedFiber(fiber)


def enqueueConcurrentRenderForLane(
    fiber: Any,
    lane: Lane,
) -> Any | None:
    enqueueUpdate(fiber, None, None, lane)
    return getRootForUpdatedFiber(fiber)


def unsafe_markUpdateLaneFromFiberToRoot(
    sourceFiber: Any,
    lane: Lane,
) -> Any | None:
    return markUpdateLaneFromFiberToRoot(sourceFiber, None, lane)


__all__ = [
    "concurrentQueues",
    "enqueueConcurrentClassUpdate",
    "enqueueConcurrentHookUpdate",
    "enqueueConcurrentHookUpdateAndEagerlyBailout",
    "enqueueConcurrentRenderForLane",
    "enqueueUpdate",
    "finishQueueingConcurrentUpdates",
    "getConcurrentlyUpdatedLanes",
    "getRootForUpdatedFiber",
    "markFiberUpdated",
    "markUpdateLaneFromFiberToRoot",
    "unsafe_markUpdateLaneFromFiberToRoot",
]
