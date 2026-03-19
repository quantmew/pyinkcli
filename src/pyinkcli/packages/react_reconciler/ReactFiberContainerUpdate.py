"""Container update and root commit helpers aligned with reconciler responsibilities."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any, Callable, Optional

from pyinkcli.hooks._runtime import _finish_hook_state
from pyinkcli.packages.ink.dom import DOMElement
from pyinkcli.packages.react_reconciler.ReactFiberReconciler import packageInfo
from pyinkcli.packages.react_reconciler.ReactFiberRoot import ReconcilerContainer

if TYPE_CHECKING:
    from pyinkcli.component import RenderableNode
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler


def createContainer(
    reconciler: "_Reconciler",
    container: DOMElement,
    tag: int = 0,
    hydrate: bool = False,
) -> ReconcilerContainer:
    reconciler_container = ReconcilerContainer(container=container, tag=tag, hydrate=hydrate)
    if reconciler._devtools_container is None:
        reconciler._devtools_container = reconciler_container
    return reconciler_container


def updateContainer(
    reconciler: "_Reconciler",
    element: "RenderableNode",
    container: ReconcilerContainer,
    parent_component: Optional[Any] = None,
    callback: Optional[Callable[[], None]] = None,
) -> None:
    if container.tag == 0:
        updateContainerSync(
            reconciler,
            element,
            container,
            parent_component=parent_component,
            callback=callback,
        )
        return

    with container.lock:
        container.pending_element = element
        container.pending_callback = callback
        if container.work_scheduled:
            return
        container.work_scheduled = True

    def run() -> None:
        while True:
            with container.lock:
                next_element = container.pending_element
                next_callback = container.pending_callback
                container.pending_element = None
                container.pending_callback = None

            commitContainerUpdate(
                reconciler,
                next_element,
                container,
                parent_component=parent_component,
                callback=next_callback,
            )

            with container.lock:
                if container.pending_element is None:
                    container.work_scheduled = False
                    return

    threading.Thread(target=run, daemon=True).start()


def updateContainerSync(
    reconciler: "_Reconciler",
    element: "RenderableNode",
    container: ReconcilerContainer,
    parent_component: Optional[Any] = None,
    callback: Optional[Callable[[], None]] = None,
) -> None:
    commitContainerUpdate(reconciler, element, container, parent_component, callback)


def flushSyncWork(
    reconciler: "_Reconciler",
    container: Optional[ReconcilerContainer] = None,
) -> None:
    if container is None:
        return

    while True:
        with container.lock:
            element = container.pending_element
            callback = container.pending_callback
            container.pending_element = None
            container.pending_callback = None
            container.work_scheduled = False

        if element is None:
            return

        commitContainerUpdate(reconciler, element, container, callback=callback)


def submitContainer(
    reconciler: "_Reconciler",
    element: "RenderableNode",
    container: ReconcilerContainer,
    parent_component: Optional[Any] = None,
    callback: Optional[Callable[[], None]] = None,
) -> None:
    if container.tag == 0:
        updateContainerSync(
            reconciler,
            element,
            container,
            parent_component=parent_component,
            callback=callback,
        )
        flushSyncWork(reconciler, container)
        return

    updateContainer(
        reconciler,
        element,
        container,
        parent_component=parent_component,
        callback=callback,
    )


def _buildRootInspectedElement() -> dict[str, Any]:
    return {
        "id": "root",
        "canEditHooks": False,
        "canEditFunctionProps": False,
        "canEditHooksAndDeletePaths": False,
        "canEditHooksAndRenamePaths": False,
        "canEditFunctionPropsDeletePaths": False,
        "canEditFunctionPropsRenamePaths": False,
        "canToggleError": False,
        "isErrored": False,
        "canToggleSuspense": False,
        "isSuspended": None,
        "hasLegacyContext": False,
        "context": None,
        "hooks": None,
        "props": None,
        "state": None,
        "key": None,
        "errors": [],
        "warnings": [],
        "suspendedBy": [],
        "suspendedByRange": None,
        "unknownSuspenders": 0,
        "owners": None,
        "env": None,
        "source": None,
        "stack": None,
        "type": "root",
        "rootType": "pyinkcli",
        "rendererPackageName": packageInfo["name"],
        "rendererVersion": packageInfo["version"],
        "plugins": {"stylex": None},
        "nativeTag": None,
    }


def _prepareNextCommitState(reconciler: "_Reconciler") -> None:
    reconciler._visited_class_component_ids.clear()
    reconciler._pending_class_component_commit_callbacks.clear()
    reconciler._pending_component_did_catch.clear()
    reconciler._commit_phase_recovery_requested = False
    reconciler._next_devtools_tree_snapshot = {
        "rootID": "root",
        "nodes": [
            {
                "id": "root",
                "parentID": None,
                "displayName": "Root",
                "elementType": "root",
                "key": None,
                "isErrorBoundary": False,
            }
        ],
    }
    reconciler._next_devtools_effective_props = {}
    reconciler._next_devtools_host_instance_ids = {id(reconciler.root_node): "root"}
    root_inspected_element = _buildRootInspectedElement()
    reconciler._next_devtools_inspected_elements = {"root": root_inspected_element}
    reconciler._next_devtools_inspected_element_fingerprints = {
        "root": reconciler._build_inspected_fingerprint(root_inspected_element)
    }


def commitContainerUpdate(
    reconciler: "_Reconciler",
    element: "RenderableNode",
    container: ReconcilerContainer,
    parent_component: Optional[Any] = None,
    callback: Optional[Callable[[], None]] = None,
) -> None:
    del parent_component
    dom_container = container.container
    _prepareNextCommitState(reconciler)
    commit_phase_recovery_needed = False

    try:
        next_index = 0
        if element is not None:
            next_index = reconciler._reconcile_children(
                dom_container,
                [element],
                (),
                0,
                "root",
            )

        reconciler._remove_extra_children(dom_container, next_index)
    finally:
        _finish_hook_state()
    reconciler._finalize_tree_snapshot()
    reconciler._dispose_stale_class_component_instances()
    commit_phase_recovery_needed = reconciler._flush_class_component_commit_callbacks()
    reconciler._after_commit(container)
    reconciler._flush_component_did_catch_callbacks(
        include_deferred=not commit_phase_recovery_needed,
    )

    if commit_phase_recovery_needed:
        reconciler.request_rerender(container, priority="default")

    if callback:
        callback()


def getEffectiveDevtoolsProps(
    reconciler: "_Reconciler",
    node_id: str,
    props: dict[str, Any],
) -> dict[str, Any]:
    base_props = reconciler._clone_inspected_value(props)
    override_props = reconciler._devtools_prop_overrides.get(node_id)
    effective_props = (
        reconciler._clone_inspected_value(override_props)
        if override_props is not None
        else base_props
    )
    target = reconciler._next_devtools_effective_props
    if target is not None:
        target[node_id] = reconciler._clone_inspected_value(effective_props)
    else:
        reconciler._devtools_effective_props[node_id] = reconciler._clone_inspected_value(
            effective_props
        )
    return effective_props


def calculateLayout(
    _reconciler: "_Reconciler",
    root: DOMElement,
) -> None:
    from pyinkcli import _yoga as yoga

    if root.yogaNode:
        root.yogaNode.calculate_layout(
            yoga.UNDEFINED,
            yoga.UNDEFINED,
            yoga.DIRECTION_LTR,
        )


__all__ = [
    "calculateLayout",
    "commitContainerUpdate",
    "createContainer",
    "flushSyncWork",
    "getEffectiveDevtoolsProps",
    "submitContainer",
    "updateContainer",
    "updateContainerSync",
]
