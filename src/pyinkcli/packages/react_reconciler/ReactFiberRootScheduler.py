"""Minimal root scheduler aligned with ReactFiberRootScheduler responsibilities."""

from __future__ import annotations

import threading
from typing import Any

from pyinkcli.packages.react_reconciler.ReactFiberLane import (
    NoLanes,
    NoLane,
    SomeTransitionLane,
)

firstScheduledRoot: Any | None = None
lastScheduledRoot: Any | None = None
currentEventTransitionLane: int = NoLane
didScheduleMicrotask: bool = False


def ensureRootIsScheduled(root: Any) -> None:
    global firstScheduledRoot, lastScheduledRoot
    if root is lastScheduledRoot or getattr(root, "next", None) is not None:
        ensureScheduleIsScheduled()
        return
    if lastScheduledRoot is None:
        firstScheduledRoot = lastScheduledRoot = root
    else:
        lastScheduledRoot.next = root
        lastScheduledRoot = root
    ensureScheduleIsScheduled()


def requestTransitionLane() -> int:
    global currentEventTransitionLane
    if currentEventTransitionLane == NoLane:
        currentEventTransitionLane = SomeTransitionLane
    return currentEventTransitionLane


def resetCurrentEventTransitionLane() -> None:
    global currentEventTransitionLane
    currentEventTransitionLane = NoLane


def resetRootSchedule() -> None:
    global firstScheduledRoot, lastScheduledRoot, didScheduleMicrotask
    current = firstScheduledRoot
    while current is not None:
        next_root = getattr(current, "next", None)
        current.next = None
        current = next_root
    firstScheduledRoot = None
    lastScheduledRoot = None
    didScheduleMicrotask = False
    resetCurrentEventTransitionLane()


def removeRootFromSchedule(root: Any) -> None:
    global firstScheduledRoot, lastScheduledRoot
    previous = None
    current = firstScheduledRoot
    while current is not None:
        next_root = getattr(current, "next", None)
        if current is root:
            if previous is None:
                firstScheduledRoot = next_root
            else:
                previous.next = next_root
            if lastScheduledRoot is root:
                lastScheduledRoot = previous
            root.next = None
            return
        previous = current
        current = next_root


def flushSyncWorkOnAllRoots() -> None:
    current = firstScheduledRoot
    while current is not None:
        next_root = getattr(current, "next", None)
        reconciler = getattr(current, "_reconciler", None)
        if reconciler is not None:
            reconciler.flush_sync_work(current)
        if (
            not getattr(current, "pending_updates", None)
            and getattr(current, "pending_lanes", NoLanes) == NoLanes
            and not getattr(current, "update_running", False)
        ):
            removeRootFromSchedule(current)
        current = next_root


def processRootScheduleInMicrotask() -> None:
    global didScheduleMicrotask
    didScheduleMicrotask = False
    flushSyncWorkOnAllRoots()


def scheduleImmediateRootScheduleTask() -> None:
    timer = threading.Timer(0.001, processRootScheduleInMicrotask)
    timer.daemon = True
    timer.start()


def ensureScheduleIsScheduled() -> None:
    global didScheduleMicrotask
    if didScheduleMicrotask:
        return
    didScheduleMicrotask = True
    scheduleImmediateRootScheduleTask()


__all__ = [
    "currentEventTransitionLane",
    "didScheduleMicrotask",
    "ensureRootIsScheduled",
    "ensureScheduleIsScheduled",
    "firstScheduledRoot",
    "flushSyncWorkOnAllRoots",
    "lastScheduledRoot",
    "processRootScheduleInMicrotask",
    "removeRootFromSchedule",
    "resetRootSchedule",
    "requestTransitionLane",
    "resetCurrentEventTransitionLane",
    "scheduleImmediateRootScheduleTask",
]
