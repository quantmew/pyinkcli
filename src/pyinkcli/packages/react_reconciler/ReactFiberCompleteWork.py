"""Minimal complete-work stub."""

from __future__ import annotations

from .ReactFiberFlags import Update
from .ReactWorkTags import ClassComponent, Fragment, HostComponent, HostRoot, HostText, SuspenseComponent


def bubbleProperties(completed_work) -> None:
    subtree_flags = 0
    child_lanes = 0
    child = getattr(completed_work, "child", None)
    while child is not None:
        subtree_flags |= getattr(child, "flags", 0)
        subtree_flags |= getattr(child, "subtree_flags", 0)
        child_lanes |= getattr(child, "lanes", 0)
        child_lanes |= getattr(child, "child_lanes", 0)
        child = getattr(child, "sibling", None)
    completed_work.subtree_flags = subtree_flags
    completed_work.child_lanes = child_lanes


def completeWork(current, work_in_progress):
    pending_props = getattr(work_in_progress, "pending_props", None)
    work_in_progress.memoized_props = pending_props
    if getattr(work_in_progress, "tag", None) == SuspenseComponent:
        work_in_progress.memoized_state = {
            "is_suspended": bool(getattr(work_in_progress, "is_suspended", False))
        }
    if getattr(work_in_progress, "state_node", None) is None and current is not None:
        work_in_progress.state_node = getattr(current, "state_node", None)
    if current is not None and getattr(current, "memoized_props", None) != pending_props:
        work_in_progress.flags = getattr(work_in_progress, "flags", 0) | Update
    bubbleProperties(work_in_progress)
    return work_in_progress


def completeTree(current, root):
    child = getattr(root, "child", None)
    contains_suspended = False
    while child is not None:
        completeTree(getattr(current, "child", None) if current is not None else None, child)
        if getattr(child, "tag", None) == SuspenseComponent:
            is_suspended = any(
                getattr(descendant, "path", ())[-1:] == ("fallback",)
                for descendant in [getattr(child, "child", None)]
                if descendant is not None
            )
            child.is_suspended = is_suspended
            child.memoized_state = {"is_suspended": is_suspended}
            contains_suspended = contains_suspended or is_suspended
        child = getattr(child, "sibling", None)
    completeWork(current, root)
    if getattr(root, "tag", None) == HostRoot:
        root.contains_suspended_fibers = contains_suspended
        root.memoized_state = {"contains_suspended_fibers": contains_suspended}
    root.is_work_in_progress = False
    node = getattr(root, "child", None)
    while node is not None:
        node.is_work_in_progress = False
        node = getattr(node, "sibling", None)
    return root


__all__ = ["bubbleProperties", "completeTree", "completeWork"]
