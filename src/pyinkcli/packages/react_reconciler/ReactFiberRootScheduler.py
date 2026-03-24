from __future__ import annotations

from .ReactFiberLane import (
    DefaultLane,
    InputContinuousLane,
    SyncLane,
    TransitionLane1,
    getHighestPriorityLane,
)

firstScheduledRoot = None
lastScheduledRoot = None
didScheduleMicrotask = False


def scheduleImmediateRootScheduleTask():
    return None


def ensureScheduleIsScheduled() -> None:
    global didScheduleMicrotask
    if not didScheduleMicrotask:
        didScheduleMicrotask = True
        scheduleImmediateRootScheduleTask()


def resetRootSchedule() -> None:
    global firstScheduledRoot, lastScheduledRoot, didScheduleMicrotask
    firstScheduledRoot = None
    lastScheduledRoot = None
    didScheduleMicrotask = False


def getRootLaneFamily(root) -> str:
    lanes = getattr(root, "pending_lanes", 0)
    if lanes & SyncLane:
        return "discrete"
    if lanes & InputContinuousLane:
        return "continuous"
    if lanes & DefaultLane:
        return "default"
    if lanes & TransitionLane1:
        return "transition"
    return "idle"


def shouldScheduleIdleWork(root) -> bool:
    return False


def getRootScheduleMode(root) -> str:
    family = getRootLaneFamily(root)
    if family == "idle":
        return "idle"
    if family in {"continuous", "transition"} and getattr(root, "tag", 0) == 1:
        return "scheduled"
    return "sync"


def ensureRootIsScheduled(root) -> None:
    global firstScheduledRoot, lastScheduledRoot
    priority = getHighestPriorityLane(getattr(root, "pending_lanes", 0))
    if priority == 0:
        return
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


def flushSyncWorkOnAllRoots() -> None:
    global firstScheduledRoot, lastScheduledRoot
    root = firstScheduledRoot
    previous = None
    while root is not None:
        next_root = getattr(root, "next", None)
        if getHighestPriorityLane(getattr(root, "pending_lanes", 0)) == SyncLane:
            root._reconciler.flush_sync_work(root)
            root.callback_priority = 0
            root.scheduled_callback_priority = 0
            if previous is None:
                firstScheduledRoot = next_root
            else:
                previous.next = next_root
            if root is lastScheduledRoot:
                lastScheduledRoot = previous
            root.next = None
        else:
            root.callback_priority = getHighestPriorityLane(getattr(root, "pending_lanes", 0))
            root.scheduled_callback_priority = root.callback_priority
            previous = root
        root = next_root


def scheduleTaskForRootDuringMicrotask(root):
    priority = getHighestPriorityLane(getattr(root, "pending_lanes", 0))
    mode = getRootScheduleMode(root)
    root.callback_priority = priority
    root.scheduled_callback_priority = priority
    return {"root": root, "next_lanes": priority, "callback_priority": priority, "mode": mode}


def processRootScheduleInMicrotask() -> None:
    global didScheduleMicrotask, firstScheduledRoot, lastScheduledRoot
    didScheduleMicrotask = False
    root = firstScheduledRoot
    while root is not None:
        scheduleTaskForRootDuringMicrotask(root)
        next_root = getattr(root, "next", None)
        if getRootScheduleMode(root) == "sync":
            root._reconciler.flush_sync_work(root)
            root.callback_priority = 0
            root.scheduled_callback_priority = 0
            root.next = None
        root = next_root
    firstScheduledRoot = None
    lastScheduledRoot = None
