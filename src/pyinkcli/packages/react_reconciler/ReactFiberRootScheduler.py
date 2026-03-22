"""Minimal root scheduler stubs."""

from __future__ import annotations

import threading

from .ReactEventPriorities import (
    ContinuousEventPriority,
    DefaultEventPriority,
    DiscreteEventPriority,
    IdleEventPriority,
    TransitionEventPriority,
    lanesToEventPriority,
)
from .ReactFiberLane import NoLane, getHighestPriorityLane
from .ReactRootTags import ConcurrentRoot

firstScheduledRoot = None
lastScheduledRoot = None
didScheduleMicrotask = False
_scheduled_timer: threading.Timer | None = None


def getLaneFamilyForPriority(priority: int) -> str:
    if priority == DiscreteEventPriority:
        return "discrete"
    if priority == ContinuousEventPriority:
        return "continuous"
    if priority == DefaultEventPriority:
        return "default"
    if priority == TransitionEventPriority:
        return "transition"
    if priority == IdleEventPriority or priority == NoLane:
        return "idle"
    return "default"


def getRootLaneFamily(root) -> str:
    lanes = getattr(root, "pending_lanes", 0)
    highest_lane = getHighestPriorityLane(lanes)
    if highest_lane == NoLane:
        return "idle"
    return getLaneFamilyForPriority(lanesToEventPriority(highest_lane))


def getRootScheduleModeForFamily(root, family: str) -> str:
    if family == "idle":
        return "scheduled" if shouldScheduleIdleWork(root) else "idle"
    if getattr(root, "tag", 0) != ConcurrentRoot:
        return "sync"
    if family in ("discrete", "default"):
        return "sync"
    return "scheduled"


def getRootScheduleMode(root) -> str:
    return getRootScheduleModeForFamily(root, getRootLaneFamily(root))


def getRootCallbackPriority(root) -> int:
    lanes = getattr(root, "pending_lanes", 0)
    highest_lane = getHighestPriorityLane(lanes)
    if highest_lane == NoLane:
        return NoLane
    return highest_lane


def isRootScheduled(root) -> bool:
    return root is firstScheduledRoot or root is lastScheduledRoot or getattr(root, "next", None) is not None


def shouldReuseScheduledTask(root, next_callback_priority: int) -> bool:
    if next_callback_priority == NoLane:
        return False
    return isRootScheduled(root) and getattr(root, "scheduled_callback_priority", NoLane) == next_callback_priority


def shouldScheduleIdleWork(root) -> bool:
    # Keep idle work unscheduled until a distinct idle host callback exists.
    return False


def updateScheduledCallbackPriority(root, next_callback_priority: int) -> None:
    root.scheduled_callback_priority = next_callback_priority
    root.callback_priority = next_callback_priority


def scheduleTaskForRootDuringMicrotask(root) -> dict[str, object]:
    next_lanes = getattr(root, "pending_lanes", NoLane)
    next_callback_priority = getHighestPriorityLane(next_lanes)
    updateScheduledCallbackPriority(root, next_callback_priority)
    return {
        "root": root,
        "next_lanes": next_lanes,
        "callback_priority": next_callback_priority,
        "mode": getRootScheduleMode(root),
    }


def processScheduledRoot(root, plan: dict[str, object] | None = None) -> None:
    if plan is None:
        plan = scheduleTaskForRootDuringMicrotask(root)
    mode = str(plan["mode"])
    reconciler = getattr(root, "_reconciler", None) or getattr(root, "reconciler", None)
    if reconciler is None:
        return
    if mode == "idle":
        updateScheduledCallbackPriority(root, NoLane)
        return
    updateScheduledCallbackPriority(root, getRootCallbackPriority(root))
    if mode == "sync":
        if hasattr(reconciler, "flush_sync_work"):
            reconciler.flush_sync_work(root)
        updateScheduledCallbackPriority(root, getRootCallbackPriority(root))
        return

    from .ReactFiberWorkLoop import performWorkOnRoot

    performWorkOnRoot(root, int(plan["next_lanes"]))
    updateScheduledCallbackPriority(root, getRootCallbackPriority(root))


def resetRootSchedule() -> None:
    global firstScheduledRoot, lastScheduledRoot, didScheduleMicrotask, _scheduled_timer
    if _scheduled_timer is not None:
        _scheduled_timer.cancel()
        _scheduled_timer = None
    firstScheduledRoot = None
    lastScheduledRoot = None
    didScheduleMicrotask = False


def ensureRootIsScheduled(root):
    global firstScheduledRoot, lastScheduledRoot
    next_callback_priority = getRootCallbackPriority(root)
    if shouldReuseScheduledTask(root, next_callback_priority):
        ensureScheduleIsScheduled()
        return
    updateScheduledCallbackPriority(root, next_callback_priority)
    if isRootScheduled(root):
        ensureScheduleIsScheduled()
        return
    if firstScheduledRoot is None:
        firstScheduledRoot = root
        lastScheduledRoot = root
        root.next = None
    elif root is not lastScheduledRoot:
        lastScheduledRoot.next = root
        lastScheduledRoot = root
        root.next = None
    ensureScheduleIsScheduled()


def scheduleImmediateRootScheduleTask():
    global _scheduled_timer

    def run() -> None:
        global _scheduled_timer
        _scheduled_timer = None
        processRootScheduleInMicrotask()

    _scheduled_timer = threading.Timer(0.001, run)
    _scheduled_timer.daemon = True
    _scheduled_timer.start()


def ensureScheduleIsScheduled() -> None:
    global didScheduleMicrotask
    if didScheduleMicrotask:
        return
    didScheduleMicrotask = True
    scheduleImmediateRootScheduleTask()


def processRootScheduleInMicrotask() -> None:
    global didScheduleMicrotask, firstScheduledRoot, lastScheduledRoot
    didScheduleMicrotask = False
    root_plans: list[tuple[object, dict[str, object]]] = []
    current = firstScheduledRoot
    while current is not None:
        next_root = getattr(current, "next", None)
        root_plans.append((current, scheduleTaskForRootDuringMicrotask(current)))
        current.next = None
        current = next_root
    for root, plan in root_plans:
        processScheduledRoot(root, plan)
    firstScheduledRoot = None
    lastScheduledRoot = None


def flushSyncWorkOnAllRoots():
    global firstScheduledRoot, lastScheduledRoot
    current = firstScheduledRoot
    while current is not None:
        next_root = getattr(current, "next", None)
        mode = getRootScheduleMode(current)
        reconciler = getattr(current, "_reconciler", None) or getattr(current, "reconciler", None)
        if mode == "sync" and reconciler is not None and hasattr(reconciler, "flush_sync_work"):
            reconciler.flush_sync_work(current)
        updateScheduledCallbackPriority(current, getRootCallbackPriority(current))
        current.next = None
        current = next_root
    firstScheduledRoot = None
    lastScheduledRoot = None


def flushSyncWorkOnLegacyRootsOnly():
    return None


__all__ = [
    "firstScheduledRoot",
    "lastScheduledRoot",
    "didScheduleMicrotask",
    "getLaneFamilyForPriority",
    "getRootLaneFamily",
    "getRootCallbackPriority",
    "isRootScheduled",
    "shouldReuseScheduledTask",
    "shouldScheduleIdleWork",
    "updateScheduledCallbackPriority",
    "scheduleTaskForRootDuringMicrotask",
    "getRootScheduleMode",
    "getRootScheduleModeForFamily",
    "resetRootSchedule",
    "ensureRootIsScheduled",
    "scheduleImmediateRootScheduleTask",
    "ensureScheduleIsScheduled",
    "processRootScheduleInMicrotask",
    "flushSyncWorkOnAllRoots",
    "flushSyncWorkOnLegacyRootsOnly",
]
