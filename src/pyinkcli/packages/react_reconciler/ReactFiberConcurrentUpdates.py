"""Minimal concurrent update helpers."""

from __future__ import annotations

from typing import Any

from .ReactFiberLane import NoLane, NoLanes, Lanes, mergeLanes


def _walk_parent_chain(fiber: Any, lane: int) -> None:
    current = fiber
    while current is not None:
        current.lanes = mergeLanes(getattr(current, "lanes", NoLanes), lane)
        current.child_lanes = mergeLanes(getattr(current, "child_lanes", NoLanes), lane)
        current = getattr(current, "return_fiber", None) or getattr(current, "return", None)


def markFiberUpdated(fiber: Any, lane: int) -> None:
    if fiber is None:
        return
    _walk_parent_chain(fiber, lane)


def unsafe_markUpdateLaneFromFiberToRoot(sourceFiber: Any, lane: int) -> Any | None:
    if sourceFiber is None:
        return None
    _walk_parent_chain(sourceFiber, lane)
    current = sourceFiber
    root = sourceFiber
    while current is not None:
        alternate = getattr(current, "alternate", None)
        if alternate is not None:
            alternate.child_lanes = mergeLanes(getattr(alternate, "child_lanes", NoLanes), lane)
        root = current
        current = getattr(current, "return_fiber", None) or getattr(current, "return", None)
    root.pending_lanes = mergeLanes(getattr(root, "pending_lanes", NoLanes), lane)
    return root


def markUpdateLaneFromFiberToRoot(sourceFiber: Any, _update: Any, lane: int) -> Any | None:
    return unsafe_markUpdateLaneFromFiberToRoot(sourceFiber, lane)


def finishQueueingConcurrentUpdates() -> None:
    return None


def getConcurrentlyUpdatedLanes() -> int:
    return NoLanes


def enqueueConcurrentHookUpdate(*_args: Any, **_kwargs: Any) -> Any | None:
    return None


def enqueueConcurrentHookUpdateAndEagerlyBailout(*_args: Any, **_kwargs: Any) -> None:
    return None


def enqueueConcurrentClassUpdate(*_args: Any, **_kwargs: Any) -> Any | None:
    return None


def enqueueConcurrentRenderForLane(*_args: Any, **_kwargs: Any) -> Any | None:
    return None


__all__ = [
    "markFiberUpdated",
    "markUpdateLaneFromFiberToRoot",
    "unsafe_markUpdateLaneFromFiberToRoot",
    "finishQueueingConcurrentUpdates",
    "getConcurrentlyUpdatedLanes",
    "enqueueConcurrentHookUpdate",
    "enqueueConcurrentHookUpdateAndEagerlyBailout",
    "enqueueConcurrentClassUpdate",
    "enqueueConcurrentRenderForLane",
]
