"""
React Fiber Root Scheduler - 根调度器

实现抢占式更新逻辑，处理多 Root 的优先级调度。
"""

from __future__ import annotations

from .ReactFiberLane import (
    DefaultLane,
    IdleLane,
    InputContinuousLane,
    NoLane,
    NoLanes,
    SyncLane,
    TransitionLanes,
    getHighestPriorityLane,
    includesBlockingLane,
    includesExpiredLane,
    includesSyncLane,
)
from .ReactEventPriorities import (
    DefaultEventPriority,
    DiscreteEventPriority,
    IdleEventPriority,
    TransitionEventPriority,
    eventPriorityToSchedulerPriority,
)

firstScheduledRoot: object | None = None
lastScheduledRoot: object | None = None
didScheduleMicrotask: bool = False
currentlyRenderingRoot: object | None = None
currentlyRenderingLane: int = NoLane
isExecutingMicrotask: bool = False


def getNextLanes(root: object, wipLanes: int, suspendedLanes: int = NoLanes) -> int:
    pendingLanes = getattr(root, "pending_lanes", NoLanes)
    if pendingLanes == NoLanes:
        return NoLanes
    availableLanes = pendingLanes & ~suspendedLanes
    if availableLanes == NoLanes:
        return NoLanes
    nextLane = getHighestPriorityLane(availableLanes)
    if wipLanes != NoLanes:
        if nextLane < getHighestPriorityLane(wipLanes):
            return nextLane
        return wipLanes
    return nextLane


def getEntangledLanes(root: object, lane: int) -> int:
    if lane == SyncLane:
        return getattr(root, "pending_lanes", NoLanes) & SyncLane
    return lane


def shouldTimeSlice(root: object, lanes: int) -> bool:
    return (
        not includesBlockingLane(lanes)
        and not includesExpiredLane(lanes)
        and not _isRootPrerendering(root)
    )


def _isRootPrerendering(root: object) -> bool:
    return getattr(root, "is_prerendering", False)


def scheduleImmediateRootScheduleTask() -> None:
    global isExecutingMicrotask
    isExecutingMicrotask = False


def ensureScheduleIsScheduled() -> None:
    global didScheduleMicrotask
    if not didScheduleMicrotask:
        didScheduleMicrotask = True
        scheduleImmediateRootScheduleTask()


def resetRootSchedule() -> None:
    global firstScheduledRoot, lastScheduledRoot, didScheduleMicrotask, currentlyRenderingRoot, currentlyRenderingLane, isExecutingMicrotask
    firstScheduledRoot = None
    lastScheduledRoot = None
    didScheduleMicrotask = False
    currentlyRenderingRoot = None
    currentlyRenderingLane = NoLane
    isExecutingMicrotask = False


def getRootLaneFamily(root: object) -> str:
    lanes = getattr(root, "pending_lanes", 0)
    if lanes & SyncLane:
        return "discrete"
    if lanes & InputContinuousLane:
        return "continuous"
    if lanes & DefaultLane:
        return "default"
    if lanes & TransitionLanes:
        return "transition"
    if lanes & IdleLane or lanes == 0:
        return "idle"
    return "unknown"


def getRootScheduleMode(root: object) -> str:
    lanes = getattr(root, "pending_lanes", NoLanes)
    tag = getattr(root, "tag", 0)
    if lanes == NoLanes or lanes & IdleLane:
        return "idle"
    if tag == 0:
        return "sync"
    if includesSyncLane(lanes) or lanes & DefaultLane or includesExpiredLane(lanes):
        return "sync"
    return "scheduled"


def shouldScheduleIdleWork(root: object) -> bool:
    return False


def ensureRootIsScheduled(root: object) -> None:
    global firstScheduledRoot, lastScheduledRoot
    pendingLanes = getattr(root, "pending_lanes", NoLanes)
    if pendingLanes == NoLanes:
        return
    priority = getHighestPriorityLane(pendingLanes)
    if _shouldInterruptCurrentRender(root, priority):
        _interruptCurrentRender(root)
    root.callback_priority = priority
    root.scheduled_callback_priority = priority
    if firstScheduledRoot is None:
        firstScheduledRoot = lastScheduledRoot = root
        root.next = None
    elif root is not firstScheduledRoot and getattr(root, "next", None) is None:
        lastScheduledRoot.next = root
        lastScheduledRoot = root
        root.next = None
    ensureScheduleIsScheduled()


def _shouldInterruptCurrentRender(root: object, nextLane: int) -> bool:
    global currentlyRenderingRoot, currentlyRenderingLane
    if currentlyRenderingRoot is not root:
        return False
    if currentlyRenderingLane == NoLane:
        return False
    return nextLane < currentlyRenderingLane and nextLane != NoLane


def _interruptCurrentRender(root: object) -> None:
    if hasattr(root, "work_in_progress"):
        wip = root.work_in_progress
        if wip is not None:
            root.saved_work_in_progress = wip
            root.saved_lanes = getattr(root, "work_in_progress_lanes", NoLanes)


def flushSyncWorkOnAllRoots() -> None:
    global firstScheduledRoot, lastScheduledRoot
    root = firstScheduledRoot
    previous = None
    while root is not None:
        next_root = getattr(root, "next", None)
        pending_lanes = getattr(root, "pending_lanes", NoLanes)
        if pending_lanes != NoLanes and getRootScheduleMode(root) == "sync":
            if hasattr(root, "_reconciler"):
                root._reconciler.flush_sync_work(root)
            root.callback_priority = NoLane
            root.scheduled_callback_priority = NoLane
            if previous is None:
                firstScheduledRoot = next_root
            else:
                previous.next = next_root
            if root is lastScheduledRoot:
                lastScheduledRoot = previous
            root.next = None
        else:
            if pending_lanes != NoLanes:
                root.callback_priority = getHighestPriorityLane(pending_lanes)
                root.scheduled_callback_priority = root.callback_priority
            previous = root
        root = next_root


def scheduleTaskForRootDuringMicrotask(root: object) -> dict | None:
    pendingLanes = getattr(root, "pending_lanes", NoLanes)
    if pendingLanes == NoLanes:
        return None
    priority = getHighestPriorityLane(pendingLanes)
    root.callback_priority = priority
    root.scheduled_callback_priority = priority
    return {
        "root": root,
        "next_lanes": priority,
        "callback_priority": priority,
        "mode": getRootScheduleMode(root),
    }


def processRootScheduleInMicrotask() -> None:
    global didScheduleMicrotask, firstScheduledRoot, lastScheduledRoot, isExecutingMicrotask
    didScheduleMicrotask = False
    isExecutingMicrotask = True
    try:
        root = firstScheduledRoot
        while root is not None:
            next_root = getattr(root, "next", None)
            task = scheduleTaskForRootDuringMicrotask(root)
            if task is not None:
                mode = task["mode"]
                lanes = task["next_lanes"]
                if hasattr(root, "_reconciler"):
                    if mode == "sync":
                        root._reconciler.flush_sync_work(root)
                        root.callback_priority = NoLane
                        root.scheduled_callback_priority = NoLane
                    else:
                        from .ReactFiberWorkLoop import performWorkOnRoot
                        performWorkOnRoot(root, lanes, force_sync=False)
            else:
                root.callback_priority = NoLane
                root.scheduled_callback_priority = NoLane
            root.next = None
            root = next_root
        firstScheduledRoot = None
        lastScheduledRoot = None
    finally:
        isExecutingMicrotask = False


def getCurrentSchedulerPriorityForLanes(lanes: int) -> int:
    if lanes == NoLanes:
        from .ReactEventPriorities import NormalSchedulerPriority
        return NormalSchedulerPriority
    from .ReactEventPriorities import lanesToEventPriority
    event_priority = lanesToEventPriority(lanes)
    return eventPriorityToSchedulerPriority(event_priority)


__all__ = [
    "firstScheduledRoot",
    "lastScheduledRoot",
    "didScheduleMicrotask",
    "currentlyRenderingRoot",
    "currentlyRenderingLane",
    "isExecutingMicrotask",
    "getNextLanes",
    "getEntangledLanes",
    "shouldTimeSlice",
    "ensureRootIsScheduled",
    "scheduleImmediateRootScheduleTask",
    "ensureScheduleIsScheduled",
    "resetRootSchedule",
    "getRootLaneFamily",
    "getRootScheduleMode",
    "shouldScheduleIdleWork",
    "flushSyncWorkOnAllRoots",
    "scheduleTaskForRootDuringMicrotask",
    "processRootScheduleInMicrotask",
    "getCurrentSchedulerPriorityForLanes",
]
