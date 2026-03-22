"""Container update and root commit helpers aligned with reconciler responsibilities."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pyinkcli.hooks._runtime import _finish_hook_state
from pyinkcli.packages.react_reconciler.ReactFiberFlags import NoFlags
from pyinkcli.packages.ink.dom import DOMElement, cloneNodeTree
from pyinkcli.packages.react_reconciler.ReactFiberBeginWork import beginWork
from pyinkcli.packages.react_reconciler.ReactFiberCompleteWork import (
    buildCompletionState,
    completeTree,
)
from pyinkcli.packages.react_reconciler.ReactEventPriorities import (
    DefaultEventPriority,
    DiscreteEventPriority,
)
from pyinkcli.packages.react_reconciler.ReactChildFiber import WorkBudget
from pyinkcli.packages.react_reconciler.ReactFiberCommitWork import (
    buildCommitListFromFiberTree,
    PreparedCommit,
    runPreparedCommitEffects,
)
from pyinkcli.packages.react_reconciler.ReactFiberRootScheduler import (
    ensureRootIsScheduled,
    removeRootFromSchedule,
)
from pyinkcli.packages.react_reconciler.ReactFiberReconciler import packageInfo
from pyinkcli.packages.react_reconciler.ReactFiberRoot import ReconcilerContainer

if TYPE_CHECKING:
    from pyinkcli.component import RenderableNode
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler

@dataclass
class ConcurrentRenderState:
    element: RenderableNode
    priority: int
    version: int
    work_root: DOMElement
    status: str = "active"
    abort_reason: str | None = None
    continuation: Callable[[], int] | None = None
    callback: Callable[[], None] | None = None
    prepared_commit: PreparedCommit | None = None


def createContainer(
    reconciler: _Reconciler,
    container: DOMElement,
    tag: int = 0,
    hydrate: bool = False,
) -> ReconcilerContainer:
    reconciler_container = ReconcilerContainer(container=container, tag=tag, hydrate=hydrate)
    reconciler_container._reconciler = reconciler
    if reconciler._devtools_container is None:
        reconciler._devtools_container = reconciler_container
    return reconciler_container


def updateContainer(
    reconciler: _Reconciler,
    element: RenderableNode,
    container: ReconcilerContainer,
    parent_component: Any | None = None,
    callback: Callable[[], None] | None = None,
) -> None:
    if container.tag == 0:
        ensureRootIsScheduled(container)
        updateContainerSync(
            reconciler,
            element,
            container,
            parent_component=parent_component,
            callback=callback,
        )
        return

    with container.lock:
        container.pending_updates.append((element, callback))
        if container.update_scheduled:
            return
        container.update_scheduled = True
    ensureRootIsScheduled(container)

    def run() -> None:
        while True:
            next_update = _dequeue_pending_update(container)
            if next_update is None:
                with container.lock:
                    container.update_scheduled = False
                return

            next_element, next_callback = next_update
            commitContainerUpdate(
                reconciler,
                next_element,
                container,
                parent_component=parent_component,
                callback=next_callback,
            )

    threading.Thread(target=run, daemon=True).start()


def updateContainerSync(
    reconciler: _Reconciler,
    element: RenderableNode,
    container: ReconcilerContainer,
    parent_component: Any | None = None,
    callback: Callable[[], None] | None = None,
) -> None:
    ensureRootIsScheduled(container)
    commitContainerUpdate(reconciler, element, container, parent_component, callback)


def _dequeue_pending_update(
    container: ReconcilerContainer,
) -> tuple[RenderableNode | None, Callable[[], None] | None] | None:
    with container.lock:
        if not container.pending_updates:
            return None
        element, callback = container.pending_updates.pop(0)
    return element, callback


def flushSyncWork(
    reconciler: _Reconciler,
    container: ReconcilerContainer | None = None,
) -> None:
    if container is None:
        return

    while True:
        next_update = _dequeue_pending_update(container)
        if next_update is None:
            with container.lock:
                container.update_scheduled = False
            if not container.pending_updates and not container.update_running:
                removeRootFromSchedule(container)
            return

        element, callback = next_update
        commitContainerUpdate(reconciler, element, container, callback=callback)


def submitContainer(
    reconciler: _Reconciler,
    element: RenderableNode,
    container: ReconcilerContainer,
    parent_component: Any | None = None,
    callback: Callable[[], None] | None = None,
) -> None:
    if container.tag == 0:
        ensureRootIsScheduled(container)
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


def _prepareNextCommitState(reconciler: _Reconciler) -> None:
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
    reconciler._render_suspended = False
    reconciler._suspended_lanes_this_render = 0
    reconciler._prepared_effects = {
        "mutation": [],
        "layout": [],
        "passive": [],
    }
    root_inspected_element = _buildRootInspectedElement()
    reconciler._next_devtools_inspected_elements = {"root": root_inspected_element}
    reconciler._next_devtools_inspected_element_fingerprints = {
        "root": reconciler._build_inspected_fingerprint(root_inspected_element)
    }


def commitContainerUpdate(
    reconciler: _Reconciler,
    element: RenderableNode,
    container: ReconcilerContainer,
    parent_component: Any | None = None,
    callback: Callable[[], None] | None = None,
) -> None:
    del parent_component
    dom_container = container.container
    host_config = reconciler._host_config
    should_defer_sync_passive_effects_to_commit = bool(
        host_config is not None
        and callable(host_config.should_defer_sync_passive_effects_to_commit)
        and host_config.should_defer_sync_passive_effects_to_commit()
    )
    _prepareNextCommitState(reconciler)
    commit_phase_recovery_needed = False
    root_fiber = reconciler._root_fiber
    reconciler._current_committed_root_child = root_fiber.child
    root_fiber.child = None
    root_fiber.sibling = None

    try:
        reconciler.push_current_fiber(root_fiber)
        next_index = 0
        if element is not None:
            next_index = beginWork(
                reconciler,
                None,
                root_fiber,
                element,
                dom_container,
                (),
                0,
                "root",
            )

        reconciler._remove_extra_children(dom_container, next_index)
    finally:
        reconciler.pop_current_fiber()
        _finish_hook_state(
            defer_passive_effects_to_commit=should_defer_sync_passive_effects_to_commit,
            defer_non_passive_hook_effects_to_commit=True,
        )
    completeTree(None, root_fiber)
    reconciler._current_committed_root_child = root_fiber.child
    prepared_commit = PreparedCommit(
        work_root=dom_container,
        commit_list=buildCommitListFromFiberTree(
            reconciler._root_fiber,
            is_static_dirty=bool(dom_container.isStaticDirty),
            root_completion_state=buildCompletionState(root_fiber),
        ),
        root_completion_state=buildCompletionState(root_fiber),
    )
    runPreparedCommitEffects(reconciler, container, prepared_commit)
    reconciler._finalize_tree_snapshot()
    reconciler._dispose_stale_class_component_instances()
    commit_phase_recovery_needed = reconciler._flush_class_component_commit_callbacks()
    reconciler._flush_component_did_catch_callbacks(
        include_deferred=not commit_phase_recovery_needed,
    )

    if commit_phase_recovery_needed:
        reconciler.schedule_update_on_fiber(container, DefaultEventPriority)

    if callback:
        callback()

    if (
        not container.pending_updates
        and not container.update_running
        and not container.render_state
    ):
        removeRootFromSchedule(container)


def beginContainerRender(
    reconciler: _Reconciler,
    element: RenderableNode,
    container: ReconcilerContainer,
    *,
    priority: int,
    callback: Callable[[], None] | None = None,
) -> bool:
    work_root = cloneNodeTree(container.container)
    assert isinstance(work_root, DOMElement)
    state = ConcurrentRenderState(
        element=element,
        priority=priority,
        version=container.pending_work_version,
        work_root=work_root,
        callback=callback,
    )
    container.render_state = state
    return resumeContainerRender(reconciler, container)


def abortContainerRender(
    _reconciler: _Reconciler,
    container: ReconcilerContainer,
    *,
    reason: str,
) -> None:
    state = container.render_state
    if not isinstance(state, ConcurrentRenderState):
        return
    state.status = "aborted"
    state.abort_reason = reason
    container.render_state = None


def shouldResumeContainerRender(
    _reconciler: _Reconciler,
    container: ReconcilerContainer,
    *,
    priority: int,
) -> bool:
    state = container.render_state
    if not isinstance(state, ConcurrentRenderState):
        return False
    if state.status != "active":
        return False
    if state.priority != priority:
        return False
    if state.version != container.pending_work_version:
        return False
    return True


def resumeContainerRender(
    reconciler: _Reconciler,
    container: ReconcilerContainer,
) -> bool:
    state = container.render_state
    if not isinstance(state, ConcurrentRenderState):
        return True
    if state.status != "active":
        container.render_state = None
        return True

    _prepareNextCommitState(reconciler)
    reconciler._current_work_budget = (
        WorkBudget(remaining=16) if state.priority > DiscreteEventPriority else None
    )
    root_fiber = reconciler._root_fiber
    reconciler._current_committed_root_child = root_fiber.child
    root_fiber.child = None
    root_fiber.sibling = None

    try:
        reconciler.push_current_fiber(root_fiber)
        if state.continuation is None:
            next_index = 0
            if state.element is not None:
                from pyinkcli.packages.react_reconciler.ReactChildFiber import WorkYield

                try:
                    next_index = beginWork(
                        reconciler,
                        None,
                        root_fiber,
                        state.element,
                        state.work_root,
                        (),
                        0,
                        "root",
                    )
                except WorkYield as yielded:
                    state.continuation = yielded.continuation
                    return False
            reconciler._remove_extra_children(state.work_root, next_index)
        else:
            from pyinkcli.packages.react_reconciler.ReactChildFiber import WorkYield

            try:
                state.continuation()
            except WorkYield as yielded:
                state.continuation = yielded.continuation
                return False
            state.continuation = None
    finally:
        reconciler._current_work_budget = None
        reconciler.pop_current_fiber()
        _finish_hook_state(
            defer_passive_effects_to_commit=True,
            defer_non_passive_hook_effects_to_commit=True,
        )

    completeTree(None, root_fiber)
    reconciler._current_committed_root_child = root_fiber.child
    finalizeContainerRender(reconciler, container)
    return True


def finalizeContainerRender(
    reconciler: _Reconciler,
    container: ReconcilerContainer,
) -> None:
    state = container.render_state
    if not isinstance(state, ConcurrentRenderState):
        return
    if state.status != "active":
        container.render_state = None
        return

    state.prepared_commit = PreparedCommit(
        work_root=state.work_root,
        commit_list=buildCommitListFromFiberTree(
            reconciler._root_fiber,
            is_static_dirty=bool(state.work_root.isStaticDirty),
            root_completion_state=buildCompletionState(reconciler._root_fiber),
        ),
        root_completion_state=buildCompletionState(reconciler._root_fiber),
        callback=state.callback,
    )
    reconciler._commit_prepared_container(
        container,
        state.prepared_commit,
    )
    reconciler._finalize_tree_snapshot()
    reconciler._dispose_stale_class_component_instances()
    commit_phase_recovery_needed = False
    reconciler._flush_component_did_catch_callbacks(
        include_deferred=not commit_phase_recovery_needed,
    )

    if commit_phase_recovery_needed:
        reconciler.schedule_update_on_fiber(container, DefaultEventPriority)

    container.render_state = None
    if state.prepared_commit.callback:
        state.prepared_commit.callback()
    if (
        not container.pending_updates
        and not container.update_running
        and not container.render_state
    ):
        removeRootFromSchedule(container)


def getEffectiveDevtoolsProps(
    reconciler: _Reconciler,
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
    _reconciler: _Reconciler,
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
    "abortContainerRender",
    "beginContainerRender",
    "resumeContainerRender",
    "submitContainer",
    "shouldResumeContainerRender",
    "updateContainer",
    "updateContainerSync",
]
