"""Work-loop helpers aligned with ReactFiberWorkLoop responsibilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyinkcli.packages.react_reconciler.ReactEventPriorities import UpdatePriority
from pyinkcli.packages.react_reconciler.ReactFiberReconciler import (
    consumePendingRerenderPriority,
)

if TYPE_CHECKING:
    from pyinkcli.packages.react_reconciler.ReactFiberRoot import ReconcilerContainer
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler


def priorityRank(priority: UpdatePriority) -> int:
    if priority == "render_phase":
        return 2
    if priority == "discrete":
        return 1
    return 0


def requestRerender(
    reconciler: "_Reconciler",
    container: "ReconcilerContainer",
    *,
    priority: UpdatePriority,
) -> None:
    host_config = reconciler._host_config
    if host_config is None:
        return

    with container.lock:
        container.rerender_requested = True
        if priorityRank(priority) > priorityRank(container.pending_rerender_priority):
            container.pending_rerender_priority = priority
        if container.rerender_running:
            return
        container.rerender_running = True

    try:
        while True:
            with container.lock:
                current_component = host_config.get_current_component()
                if not container.rerender_requested or current_component is None:
                    container.rerender_running = False
                    return
                container.rerender_requested = False
                container.current_render_priority = container.pending_rerender_priority
                container.pending_rerender_priority = "default"

            host_config.perform_render(current_component)
            if container.current_render_priority != "render_phase":
                host_config.wait_for_render_flush(1.0)
    finally:
        with container.lock:
            container.rerender_running = False
            container.current_render_priority = "default"


def drainPendingRerenders(
    reconciler: "_Reconciler",
    container: "ReconcilerContainer",
) -> None:
    priority = consumePendingRerenderPriority()
    if priority is None:
        return

    requestRerender(reconciler, container, priority=priority)


def dispatchCommitRender(
    reconciler: "_Reconciler",
    container: "ReconcilerContainer",
) -> None:
    reconciler._request_host_render(container.current_render_priority, immediate=False)


__all__ = [
    "dispatchCommitRender",
    "drainPendingRerenders",
    "priorityRank",
    "requestRerender",
]
