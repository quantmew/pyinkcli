"""Small work-loop facade used by compatibility imports."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .ReactEventPriorities import (
    DefaultEventPriority,
    DiscreteEventPriority,
    TransitionEventPriority,
    lanesToEventPriority,
)
from .ReactFiberLane import NoLanes, getHighestPriorityLane, mergeLanes, removeLanes
from .ReactSharedInternals import shared_internals
from .dispatcher import batchedUpdates, discreteUpdates, flushDeferredPassiveEffects

NoContext = 0
RenderContext = 1 << 0
CommitContext = 1 << 1

_execution_context = NoContext
_work_in_progress_root: Any | None = None
_work_in_progress_root_render_lanes: int = NoLanes
_root_with_pending_passive_effects: Any | None = None
_pending_passive_effects_lanes: int = NoLanes
_has_pending_commit_effects = False
_work_loop_suspended_on_data = False


def getExecutionContext() -> int:
    return _execution_context


def getWorkInProgressRoot() -> Any | None:
    return _work_in_progress_root


def getWorkInProgressRootRenderLanes() -> int:
    return _work_in_progress_root_render_lanes


def getRootWithPendingPassiveEffects() -> Any | None:
    return _root_with_pending_passive_effects


def getPendingPassiveEffectsLanes() -> int:
    return _pending_passive_effects_lanes


def hasPendingCommitEffects() -> bool:
    return _has_pending_commit_effects


def isWorkLoopSuspendedOnData() -> bool:
    return _work_loop_suspended_on_data


def performWorkOnRoot(root: Any, lanes: int) -> None:
    reconciler = getattr(root, "reconciler", None) or getattr(root, "_reconciler", None)
    if reconciler is not None and hasattr(reconciler, "flush_scheduled_updates"):
        selected_lanes = getHighestPriorityLane(lanes)
        if selected_lanes == NoLanes:
            return
        reconciler.flush_scheduled_updates(
            getattr(root, "container", None),
            lanesToEventPriority(selected_lanes),
            lanes=selected_lanes,
            consume_all=False,
        )


def flushPendingEffects() -> None:
    global _root_with_pending_passive_effects, _pending_passive_effects_lanes, _has_pending_commit_effects
    flushDeferredPassiveEffects()
    _root_with_pending_passive_effects = None
    _pending_passive_effects_lanes = NoLanes
    _has_pending_commit_effects = False


def flushPendingEffectsDelayed() -> None:
    flushPendingEffects()


def isAlreadyRendering() -> bool:
    return _execution_context != NoContext


def flushSyncFromReconciler(callback: Callable[[], Any]) -> Any:
    return callback()


def flushSyncWork() -> None:
    return None


def deferredUpdates(callback: Callable[[], Any]) -> Any:
    return batchedUpdates(callback)


def laneToMask(priority: int) -> int:
    return priority


def requestUpdateLane() -> int:
    if shared_internals.current_transition is not None:
        return TransitionEventPriority
    if shared_internals.current_update_priority:
        return shared_internals.current_update_priority
    return DefaultEventPriority


__all__ = [
    "NoContext",
    "RenderContext",
    "CommitContext",
    "getExecutionContext",
    "getWorkInProgressRoot",
    "getWorkInProgressRootRenderLanes",
    "getRootWithPendingPassiveEffects",
    "getPendingPassiveEffectsLanes",
    "hasPendingCommitEffects",
    "isWorkLoopSuspendedOnData",
    "performWorkOnRoot",
    "flushPendingEffects",
    "flushPendingEffectsDelayed",
    "isAlreadyRendering",
    "flushSyncFromReconciler",
    "flushSyncWork",
    "batchedUpdates",
    "deferredUpdates",
    "discreteUpdates",
    "getHighestPriorityLane",
    "mergeLanes",
    "removeLanes",
    "laneToMask",
    "requestUpdateLane",
]
