from __future__ import annotations

from .ReactEventPriorities import DefaultEventPriority
from .ReactFiberLane import getHighestPriorityLane
from .ReactSharedInternals import shared_internals

_work_in_progress_root = None
_work_in_progress_root_render_lanes = 0
_root_with_pending_passive_effects = None
_pending_passive_effect_lanes = 0
_has_pending_commit_effects = False


def laneToMask(priority: int) -> int:
    return priority


def requestUpdateLane() -> int:
    if getattr(shared_internals, "current_transition", None) is not None:
        from .ReactEventPriorities import TransitionEventPriority

        return TransitionEventPriority
    priority = getattr(shared_internals, "current_update_priority", None)
    if priority in (None, 0):
        return DefaultEventPriority
    return priority


def performWorkOnRoot(root, lanes: int) -> None:
    selected = getHighestPriorityLane(lanes)
    root._reconciler.flush_scheduled_updates(root.container, selected, lanes=selected, consume_all=False)


def mergeLanes(a: int, b: int) -> int:
    return a | b


def removeLanes(a: int, b: int) -> int:
    return a & ~b


def getWorkInProgressRoot():
    return _work_in_progress_root


def getWorkInProgressRootRenderLanes():
    return _work_in_progress_root_render_lanes


def getRootWithPendingPassiveEffects():
    return _root_with_pending_passive_effects


def getPendingPassiveEffectsLanes():
    return _pending_passive_effect_lanes


def hasPendingCommitEffects():
    return _has_pending_commit_effects


def flushPendingEffects() -> None:
    global _root_with_pending_passive_effects, _pending_passive_effect_lanes
    global _has_pending_commit_effects
    from ...hooks import _runtime as hooks_runtime

    for fiber in list(getattr(hooks_runtime._runtime, "pending_passive_unmount_fibers", [])):
        hook = getattr(fiber, "hook_head", None)
        if hook and callable(getattr(hook, "cleanup", None)):
            hook.cleanup()
    getattr(hooks_runtime._runtime, "pending_passive_unmount_fibers", []).clear()
    for hook in list(getattr(hooks_runtime._runtime, "pending_passive_mount_effects", [])):
        if callable(getattr(hook, "cleanup", None)):
            hook.cleanup()
        hook.cleanup = hook.callback() if callable(hook.callback) else None
        hook.needs_run = False
        hook.queued = False
    getattr(hooks_runtime._runtime, "pending_passive_mount_effects", []).clear()
    for fiber in getattr(hooks_runtime._runtime, "fibers", {}).values():
        queue = getattr(fiber, "update_queue", None)
        effect = getattr(queue, "last_effect", None)
        if effect is not None and callable(effect.create):
            effect.create()
    hooks_runtime._runtime.fibers = {}
    _root_with_pending_passive_effects = None
    _pending_passive_effect_lanes = 0
    _has_pending_commit_effects = False
