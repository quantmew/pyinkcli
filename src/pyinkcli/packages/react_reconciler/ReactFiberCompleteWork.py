"""Complete-work helpers aligned with ReactFiberCompleteWork responsibilities."""

from __future__ import annotations

from typing import Any

from pyinkcli.packages.react_reconciler.ReactFiberFlags import NoFlags, Update
from pyinkcli.packages.react_reconciler.ReactFiberLane import NoLanes
from pyinkcli.packages.react_reconciler.ReactWorkTags import (
    ClassComponent,
    Fragment,
    HostComponent,
    HostRoot,
    HostText,
    SuspenseComponent,
)


def markUpdate(workInProgress: Any) -> None:
    workInProgress.flags |= Update


def isMountingFiber(current: Any, workInProgress: Any) -> bool:
    del workInProgress
    return current is None


def finalizeStateNode(current: Any, workInProgress: Any) -> None:
    if getattr(workInProgress, "state_node", None) is not None:
        return
    if current is not None and getattr(current, "state_node", None) is not None:
        workInProgress.state_node = current.state_node


def finalizeProps(workInProgress: Any) -> None:
    if hasattr(workInProgress, "pending_props"):
        workInProgress.memoized_props = workInProgress.pending_props
    if hasattr(workInProgress, "pending_children"):
        workInProgress.memoized_children = workInProgress.pending_children


def finalizeFiber(workInProgress: Any) -> None:
    finalizeProps(workInProgress)
    if hasattr(workInProgress, "current_hook"):
        workInProgress.current_hook = None
    if hasattr(workInProgress, "is_work_in_progress"):
        workInProgress.is_work_in_progress = False


def propsChanged(current: Any, workInProgress: Any) -> bool:
    if current is None:
        return False
    previous = getattr(current, "memoized_props", None)
    pending = getattr(workInProgress, "pending_props", None)
    return previous != pending


def shouldMarkUpdate(current: Any, workInProgress: Any) -> bool:
    if isMountingFiber(current, workInProgress):
        return False
    return propsChanged(current, workInProgress)


def bubbleProperties(completedWork: Any) -> None:
    subtree_flags = NoFlags
    child_lanes = NoLanes
    child = getattr(completedWork, "child", None)
    while child is not None:
        subtree_flags |= getattr(child, "flags", NoFlags)
        subtree_flags |= getattr(child, "subtree_flags", NoFlags)
        child_lanes |= getattr(child, "lanes", NoLanes)
        child_lanes |= getattr(child, "child_lanes", NoLanes)
        child = getattr(child, "sibling", None)
    completedWork.subtree_flags = subtree_flags
    completedWork.child_lanes = child_lanes


def _iter_subtree_fibers(root: Any, seen: set[int] | None = None):
    if seen is None:
        seen = set()
    child = getattr(root, "child", None)
    while child is not None:
        child_id = id(child)
        if child_id in seen:
            child = getattr(child, "sibling", None)
            continue
        seen.add(child_id)
        yield child
        yield from _iter_subtree_fibers(child, seen)
        child = getattr(child, "sibling", None)


def inferSuspenseFallbackState(workInProgress: Any) -> bool:
    for fiber in _iter_subtree_fibers(workInProgress):
        path = getattr(fiber, "path", ()) or ()
        if "fallback" in path:
            return True
    return False


def completeHostText(current: Any, workInProgress: Any) -> Any:
    if shouldMarkUpdate(current, workInProgress):
        markUpdate(workInProgress)
    finalizeStateNode(current, workInProgress)
    finalizeFiber(workInProgress)
    return workInProgress


def completeHostComponent(current: Any, workInProgress: Any) -> Any:
    if shouldMarkUpdate(current, workInProgress):
        markUpdate(workInProgress)
    finalizeStateNode(current, workInProgress)
    finalizeFiber(workInProgress)
    return workInProgress


def completeHostRoot(current: Any, workInProgress: Any) -> Any:
    finalizeStateNode(current, workInProgress)
    contains_suspended_fibers = any(
        bool(getattr(fiber, "is_suspended", False)) for fiber in _iter_subtree_fibers(workInProgress)
    )
    workInProgress.contains_suspended_fibers = contains_suspended_fibers
    workInProgress.memoized_state = {
        "contains_suspended_fibers": contains_suspended_fibers,
    }
    finalizeFiber(workInProgress)
    return workInProgress


def completeClassComponent(current: Any, workInProgress: Any) -> Any:
    if shouldMarkUpdate(current, workInProgress):
        markUpdate(workInProgress)
    finalizeStateNode(current, workInProgress)
    finalizeFiber(workInProgress)
    return workInProgress


def completeFragment(current: Any, workInProgress: Any) -> Any:
    if shouldMarkUpdate(current, workInProgress):
        markUpdate(workInProgress)
    finalizeStateNode(current, workInProgress)
    finalizeFiber(workInProgress)
    return workInProgress


def completeSuspenseComponent(current: Any, workInProgress: Any) -> Any:
    if shouldMarkUpdate(current, workInProgress):
        markUpdate(workInProgress)
    finalizeStateNode(current, workInProgress)
    is_suspended = inferSuspenseFallbackState(workInProgress)
    workInProgress.is_suspended = is_suspended
    workInProgress.memoized_state = {"is_suspended": is_suspended}
    finalizeFiber(workInProgress)
    return workInProgress


def completeWork(current: Any, workInProgress: Any) -> Any:
    tag = getattr(workInProgress, "tag", None)
    if tag == HostText:
        completeHostText(current, workInProgress)
    elif tag == HostComponent:
        completeHostComponent(current, workInProgress)
    elif tag == HostRoot:
        completeHostRoot(current, workInProgress)
    elif tag == ClassComponent:
        completeClassComponent(current, workInProgress)
    elif tag == Fragment:
        completeFragment(current, workInProgress)
    elif tag == SuspenseComponent:
        completeSuspenseComponent(current, workInProgress)
    bubbleProperties(workInProgress)
    return workInProgress


def completeTree(current: Any, workInProgress: Any, seen: set[int] | None = None) -> Any:
    if workInProgress is None:
        return None
    if seen is None:
        seen = set()
    fiber_id = id(workInProgress)
    if fiber_id in seen:
        return workInProgress
    seen.add(fiber_id)
    if getattr(workInProgress, "did_bailout", False):
        return completeWork(current, workInProgress)
    child = getattr(workInProgress, "child", None)
    while child is not None:
        completeTree(getattr(child, "alternate", None), child, seen)
        child = getattr(child, "sibling", None)
    return completeWork(current, workInProgress)


def buildCompletionState(workInProgress: Any) -> dict[str, Any]:
    return {
        "tag": getattr(workInProgress, "tag", None),
        "memoizedProps": getattr(workInProgress, "memoized_props", None),
        "memoizedState": getattr(workInProgress, "memoized_state", None),
        "containsSuspendedFibers": bool(getattr(workInProgress, "contains_suspended_fibers", False)),
        "subtreeFlags": getattr(workInProgress, "subtree_flags", NoFlags),
        "flags": getattr(workInProgress, "flags", NoFlags),
    }


__all__ = [
    "bubbleProperties",
    "buildCompletionState",
    "completeClassComponent",
    "completeFragment",
    "completeHostComponent",
    "completeHostRoot",
    "completeHostText",
    "completeSuspenseComponent",
    "completeTree",
    "completeWork",
    "finalizeFiber",
    "finalizeProps",
    "finalizeStateNode",
    "inferSuspenseFallbackState",
    "isMountingFiber",
    "markUpdate",
    "propsChanged",
    "shouldMarkUpdate",
]
