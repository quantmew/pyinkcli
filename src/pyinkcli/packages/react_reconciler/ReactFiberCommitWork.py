"""Commit-phase helpers aligned with ReactFiberCommitWork responsibilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyinkcli.packages.ink.dom import emitLayoutListeners
from pyinkcli.packages.react_reconciler.ReactEventPriorities import UpdatePriority

if TYPE_CHECKING:
    from pyinkcli.packages.react_reconciler.ReactFiberRoot import ReconcilerContainer
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler


def _assign_ref(ref: Any, value: Any) -> None:
    if ref is None:
        return

    if callable(ref):
        ref(value)
        return

    if isinstance(ref, dict):
        ref["current"] = value
        return

    if hasattr(ref, "current"):
        ref.current = value


def _collect_host_refs(node: Any, refs: dict[int, tuple[Any, Any]]) -> None:
    child_nodes = getattr(node, "childNodes", None)
    if child_nodes is None:
        return

    internal_ref = getattr(node, "internal_ref", None)
    if internal_ref is not None:
        refs[id(node)] = (internal_ref, node)

    for child in child_nodes:
        _collect_host_refs(child, refs)


def _sync_host_refs(reconciler: "_Reconciler", root: Any) -> None:
    previous_refs = getattr(reconciler, "_attached_host_refs", {})
    next_refs: dict[int, tuple[Any, Any]] = {}
    _collect_host_refs(root, next_refs)

    for node_id, (ref, _node) in previous_refs.items():
        next_entry = next_refs.get(node_id)
        if next_entry is None or next_entry[0] is not ref:
            _assign_ref(ref, None)

    for node_id, (ref, node) in next_refs.items():
        previous_entry = previous_refs.get(node_id)
        if previous_entry is None or previous_entry[0] is not ref:
            _assign_ref(ref, node)

    reconciler._attached_host_refs = next_refs


def requestHostRender(
    reconciler: "_Reconciler",
    priority: UpdatePriority,
    *,
    immediate: bool,
) -> None:
    if reconciler._host_config is not None:
        reconciler._host_config.request_render(priority, immediate)
        return

    if immediate:
        if reconciler._on_immediate_commit is not None:
            reconciler._on_immediate_commit()
        return

    if reconciler._on_commit is not None:
        reconciler._on_commit()


def resetAfterCommit(
    reconciler: "_Reconciler",
    container: "ReconcilerContainer",
) -> None:
    dom_container = container.container
    if callable(dom_container.onComputeLayout):
        dom_container.onComputeLayout()
    elif dom_container.yogaNode:
        reconciler._calculate_layout(dom_container)

    _sync_host_refs(reconciler, dom_container)
    emitLayoutListeners(dom_container)

    if dom_container.isStaticDirty:
        dom_container.isStaticDirty = False
        requestHostRender(reconciler, container.current_render_priority, immediate=True)
        return

    requestHostRender(reconciler, container.current_render_priority, immediate=False)


__all__ = ["requestHostRender", "resetAfterCommit"]
