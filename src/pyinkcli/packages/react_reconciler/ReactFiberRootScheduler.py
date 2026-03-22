"""Minimal root scheduler stubs."""

from __future__ import annotations

firstScheduledRoot = None
lastScheduledRoot = None
didScheduleMicrotask = False


def resetRootSchedule() -> None:
    global firstScheduledRoot, lastScheduledRoot, didScheduleMicrotask
    firstScheduledRoot = None
    lastScheduledRoot = None
    didScheduleMicrotask = False


def ensureRootIsScheduled(root):
    global firstScheduledRoot, lastScheduledRoot
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
    return None


def ensureScheduleIsScheduled() -> None:
    global didScheduleMicrotask
    if didScheduleMicrotask:
        return
    didScheduleMicrotask = True
    scheduleImmediateRootScheduleTask()


def processRootScheduleInMicrotask() -> None:
    global didScheduleMicrotask
    didScheduleMicrotask = False
    flushSyncWorkOnAllRoots()


def flushSyncWorkOnAllRoots():
    global firstScheduledRoot, lastScheduledRoot
    current = firstScheduledRoot
    while current is not None:
        next_root = getattr(current, "next", None)
        reconciler = getattr(current, "_reconciler", None) or getattr(current, "reconciler", None)
        if reconciler is not None and hasattr(reconciler, "flush_sync_work"):
            reconciler.flush_sync_work(current)
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
    "resetRootSchedule",
    "ensureRootIsScheduled",
    "scheduleImmediateRootScheduleTask",
    "ensureScheduleIsScheduled",
    "processRootScheduleInMicrotask",
    "flushSyncWorkOnAllRoots",
    "flushSyncWorkOnLegacyRootsOnly",
]
