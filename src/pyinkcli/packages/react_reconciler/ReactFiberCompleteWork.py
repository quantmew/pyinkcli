from __future__ import annotations

from .ReactFiberFlags import Update
from .ReactWorkTags import HostRoot, SuspenseComponent


def bubbleProperties(parent) -> None:
    subtree_flags = 0
    child_lanes = 0
    child = getattr(parent, "child", None)
    while child is not None:
        subtree_flags |= getattr(child, "flags", 0) | getattr(child, "subtree_flags", 0)
        child_lanes |= getattr(child, "lanes", 0) | getattr(child, "child_lanes", 0)
        child = getattr(child, "sibling", None)
    parent.subtree_flags = subtree_flags
    parent.child_lanes = child_lanes


def completeWork(current, work_in_progress) -> None:
    work_in_progress.memoized_props = getattr(work_in_progress, "pending_props", None)
    if current is not None and getattr(work_in_progress, "state_node", None) is None:
        work_in_progress.state_node = getattr(current, "state_node", None)
    if current is not None and getattr(current, "memoized_props", None) != getattr(work_in_progress, "pending_props", None):
        work_in_progress.flags |= Update
    if getattr(work_in_progress, "tag", None) == SuspenseComponent:
        work_in_progress.memoized_state = {"is_suspended": False}


def completeTree(current, root) -> None:
    child = getattr(root, "child", None)
    contains_suspended = False

    def walk(node):
        nonlocal contains_suspended
        if node is None:
            return
        if getattr(node, "tag", None) == SuspenseComponent and getattr(node, "child", None) is not None:
            node.is_suspended = True
            node.memoized_state = {"is_suspended": True}
            contains_suspended = True
        if getattr(node, "tag", None) != SuspenseComponent or not contains_suspended:
            completeWork(None, node)
        if hasattr(node, "is_work_in_progress"):
            node.is_work_in_progress = False
        walk(getattr(node, "child", None))
        walk(getattr(node, "sibling", None))

    walk(child)
    completeWork(current, root)
    if getattr(root, "tag", None) == HostRoot:
        root.contains_suspended_fibers = contains_suspended
        root.memoized_state = {"contains_suspended_fibers": contains_suspended}
    if hasattr(root, "is_work_in_progress"):
        root.is_work_in_progress = False
