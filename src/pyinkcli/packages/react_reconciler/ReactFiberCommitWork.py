"""Commit-phase helpers aligned with ReactFiberCommitWork responsibilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyinkcli.packages.ink.dom import emitLayoutListeners
from pyinkcli.packages.react_reconciler.ReactEventPriorities import UpdatePriority

if TYPE_CHECKING:
    from pyinkcli.packages.react_reconciler.ReactFiberRoot import ReconcilerContainer
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler


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

    emitLayoutListeners(dom_container)

    if dom_container.isStaticDirty:
        dom_container.isStaticDirty = False
        requestHostRender(reconciler, container.current_render_priority, immediate=True)
        return

    requestHostRender(reconciler, container.current_render_priority, immediate=False)


__all__ = ["requestHostRender", "resetAfterCommit"]
