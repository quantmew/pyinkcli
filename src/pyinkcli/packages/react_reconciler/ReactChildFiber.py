"""Child reconciliation helpers aligned with ReactChildFiber responsibilities."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pyinkcli._component_runtime import (
    _is_component_class,
    isElement,
    renderComponent,
)
from pyinkcli._suspense_runtime import SuspendSignal
from pyinkcli.hooks._runtime import HookFiber, _commit_completed_fiber
from pyinkcli.packages.react.dispatcher import (
    beginComponentRender,
    endComponentRender,
    getHookStateSnapshot,
    setCurrentHookFiber,
)
from pyinkcli.packages.react_reconciler.ReactCurrentFiber import (
    resetCurrentFiber,
    setCurrentFiber,
    setIsRendering,
)
from pyinkcli.packages.react_reconciler.ReactFiberBeginWork import beginWork
from pyinkcli.packages.react_reconciler.ReactFiberLane import NoLanes
from pyinkcli.packages.react_reconciler.ReactFiberThenable import (
    createSuspendedThenableRecord,
)
from pyinkcli.packages.react_reconciler.ReactFiberUnwindWork import (
    unwindInterruptedWork,
)
from pyinkcli.packages.react_reconciler.ReactFiberHooks import (
    finishRenderingHooks,
    renderWithHooks,
)
from pyinkcli.packages.react_reconciler.ReactFiberHostContext import getChildHostContext
from pyinkcli.packages.react_reconciler.ReactFiberWorkLoop import laneToMask
from pyinkcli.packages.react_reconciler.ReactWorkTags import (
    ClassComponent,
    Fragment,
    FunctionComponent,
    HostComponent,
    HostText,
    SuspenseComponent,
)

if TYPE_CHECKING:
    from pyinkcli.component import RenderableNode
    from pyinkcli.packages.ink.dom import DOMElement
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler


@dataclass
class WorkBudget:
    remaining: int | None = None

    def consume(self) -> None:
        if self.remaining is None:
            return
        self.remaining -= 1

    def should_yield(self) -> bool:
        return self.remaining is not None and self.remaining <= 0


class WorkYield(Exception):
    def __init__(self, continuation: Callable[[], int]):
        super().__init__("render work yielded")
        self.continuation = continuation


def _is_fiber_in_current_tree(
    reconciler: _Reconciler,
    target_fiber: HookFiber | None,
) -> bool:
    if target_fiber is None:
        return False
    committed_root_child = getattr(reconciler, "_current_committed_root_child", None)
    root = committed_root_child if committed_root_child is not None else getattr(reconciler, "_root_fiber", None)
    stack = [root]
    seen: set[int] = set()
    while stack:
        current = stack.pop()
        if current is None:
            continue
        current_id = id(current)
        if current_id in seen:
            continue
        seen.add(current_id)
        if current is target_fiber:
            return True
        child = getattr(current, "child", None)
        while child is not None:
            stack.append(child)
            child = getattr(child, "sibling", None)
    return False


def _get_current_tree_fiber(
    reconciler: _Reconciler,
    component_id: str,
) -> HookFiber | None:
    stack = [getattr(reconciler, "_current_committed_root_child", None)]
    seen: set[int] = set()
    while stack:
        current = stack.pop()
        if current is None:
            continue
        current_id = id(current)
        if current_id in seen:
            continue
        seen.add(current_id)
        if getattr(current, "component_id", None) == component_id:
            return current
        child = getattr(current, "child", None)
        while child is not None:
            stack.append(child)
            child = getattr(child, "sibling", None)
    return None


def reconcileChildren(
    reconciler: _Reconciler,
    parent: DOMElement,
    children: list[RenderableNode],
    path: tuple[Any, ...],
    dom_index: int,
    devtools_parent_id: str,
) -> int:
    return _reconcile_children_range(
        reconciler,
        parent,
        children,
        path,
        dom_index,
        devtools_parent_id,
        start_index=0,
    )


def _reconcile_children_range(
    reconciler: _Reconciler,
    parent: DOMElement,
    children: list[RenderableNode],
    path: tuple[Any, ...],
    dom_index: int,
    devtools_parent_id: str,
    *,
    start_index: int,
) -> int:
    parent_fiber = reconciler._current_fiber
    if parent_fiber is not None:
        parent_fiber.child = None
    for index in range(start_index, len(children)):
        child = children[index]
        child_path = path + (getChildPathToken(reconciler, child, index),)
        dom_index = reconcileChild(
            reconciler,
            child,
            parent,
            child_path,
            dom_index,
            devtools_parent_id,
        )
        budget = getattr(reconciler, "_current_work_budget", None)
        if isinstance(budget, WorkBudget):
            budget.consume()
            if budget.should_yield() and index + 1 < len(children):
                raise WorkYield(
                    lambda: _reconcile_children_range(
                        reconciler,
                        parent,
                        children,
                        path,
                        dom_index,
                        devtools_parent_id,
                        start_index=index + 1,
                    )
                )
    return dom_index


# Dispatcher

def reconcileChild(
    reconciler: _Reconciler,
    vnode: RenderableNode,
    parent: DOMElement,
    path: tuple[Any, ...],
    dom_index: int,
    devtools_parent_id: str,
) -> int:
    return beginWork(
        reconciler,
        None,
        None,
        vnode,
        parent,
        path,
        dom_index,
        devtools_parent_id,
    )


# Boundary Lifecycle

def _append_child_fiber(
    reconciler: _Reconciler,
    parent_fiber: HookFiber | None,
    child_fiber: HookFiber,
) -> None:
    reconciler._fiber_nodes[child_fiber.component_id] = child_fiber
    if parent_fiber is None:
        return

    child_fiber.return_fiber = parent_fiber
    child_fiber.sibling = None
    if parent_fiber.child is None:
        parent_fiber.child = child_fiber
        return

    sibling = parent_fiber.child
    while sibling.sibling is not None:
        sibling = sibling.sibling
    sibling.sibling = child_fiber


def _create_or_reuse_structural_fiber(
    reconciler: _Reconciler,
    *,
    component_id: str,
    tag: int,
    element_type: str,
    key: str | None,
    path: tuple[Any, ...],
    pending_props: dict[str, Any] | None,
    pending_children: tuple[Any, ...] | None,
    return_fiber: HookFiber | None,
) -> HookFiber:
    current = _get_current_tree_fiber(reconciler, component_id)
    if current is None or getattr(current, "tag", None) != tag:
        return HookFiber(
            component_id=component_id,
            tag=tag,
            element_type=element_type,
            key=key,
            path=path,
            pending_props=pending_props,
            memoized_props=None,
            pending_children=pending_children,
            memoized_children=None,
            return_fiber=return_fiber,
            lanes=NoLanes,
            child_lanes=NoLanes,
        )

    work_in_progress = current.alternate
    if work_in_progress is None:
        work_in_progress = HookFiber(
            component_id=component_id,
            tag=tag,
            element_type=element_type,
            key=key,
            path=path,
            pending_props=pending_props,
            memoized_props=current.memoized_props,
            pending_children=pending_children,
            memoized_children=getattr(current, "memoized_children", None),
            return_fiber=return_fiber,
            lanes=current.lanes,
            child_lanes=current.child_lanes,
            dependencies=list(getattr(current, "dependencies", [])),
            runtime_source_deps=list(getattr(current, "runtime_source_deps", [])),
        )
        work_in_progress.alternate = current
        current.alternate = work_in_progress
    else:
        work_in_progress.tag = tag
        work_in_progress.element_type = element_type
        work_in_progress.key = key
        work_in_progress.path = path
        work_in_progress.pending_props = pending_props
        work_in_progress.memoized_props = current.memoized_props
        work_in_progress.pending_children = pending_children
        work_in_progress.memoized_children = getattr(current, "memoized_children", None)
        work_in_progress.return_fiber = return_fiber
        work_in_progress.lanes = current.lanes
        work_in_progress.child_lanes = current.child_lanes
        work_in_progress.dependencies = list(getattr(current, "dependencies", []))
        work_in_progress.runtime_source_deps = list(getattr(current, "runtime_source_deps", []))

    work_in_progress.child = None
    work_in_progress.sibling = None
    work_in_progress.state_node = current.state_node
    work_in_progress.is_work_in_progress = True
    return work_in_progress


def _begin_structural_fiber(
    reconciler: _Reconciler,
    parent_fiber: HookFiber | None,
    fiber: HookFiber,
) -> HookFiber:
    return _begin_fiber_boundary(
        reconciler,
        parent_fiber,
        fiber,
        prepare=_prepare_structural_fiber_boundary,
        enter=_enter_structural_fiber_boundary,
    )


def _end_structural_fiber(
    reconciler: _Reconciler,
    fiber: HookFiber,
) -> None:
    _complete_fiber_boundary(
        reconciler,
        fiber,
        complete=_complete_structural_fiber_boundary,
    )


def _begin_function_fiber(
    reconciler: _Reconciler,
    parent_fiber: HookFiber | None,
    fiber: HookFiber,
) -> HookFiber:
    return _begin_fiber_boundary(
        reconciler,
        parent_fiber,
        fiber,
        prepare=_prepare_function_fiber_boundary,
        enter=_enter_function_fiber_boundary,
    )


def _end_function_fiber(
    reconciler: _Reconciler,
    fiber: HookFiber,
) -> None:
    _complete_fiber_boundary(
        reconciler,
        fiber,
        complete=_complete_function_fiber_boundary,
    )


def _complete_structural_fiber_boundary(fiber: HookFiber) -> HookFiber:
    return _commit_completed_fiber(fiber)


def _complete_function_fiber_boundary(fiber: HookFiber) -> HookFiber:
    setCurrentHookFiber(None)
    setIsRendering(False)
    resetCurrentFiber()
    finishRenderingHooks()
    return endComponentRender() or fiber


def _prepare_structural_fiber_boundary(fiber: HookFiber) -> HookFiber:
    return fiber


def _prepare_function_fiber_boundary(fiber: HookFiber) -> HookFiber:
    setCurrentFiber(fiber)
    setIsRendering(True)
    return beginComponentRender(fiber)


def _enter_structural_fiber_boundary(fiber: HookFiber) -> None:
    return None


def _enter_function_fiber_boundary(fiber: HookFiber) -> None:
    setCurrentHookFiber(fiber)


def _begin_fiber_boundary(
    reconciler: _Reconciler,
    parent_fiber: HookFiber | None,
    fiber: HookFiber,
    *,
    prepare: Callable[[HookFiber], HookFiber],
    enter: Callable[[HookFiber], None],
) -> HookFiber:
    work_in_progress_fiber = prepare(fiber)
    _append_child_fiber(reconciler, parent_fiber, work_in_progress_fiber)
    reconciler.push_current_fiber(work_in_progress_fiber)
    enter(work_in_progress_fiber)
    return work_in_progress_fiber


def _finalize_completed_fiber_boundary(
    reconciler: _Reconciler,
    previous_fiber: HookFiber,
    fiber: HookFiber,
) -> HookFiber:
    fiber.return_fiber = previous_fiber.return_fiber
    fiber.sibling = previous_fiber.sibling
    parent_fiber = previous_fiber.return_fiber
    if parent_fiber is not None:
        current_child = parent_fiber.child
        previous_sibling = None
        while current_child is not None:
            if current_child is previous_fiber:
                if previous_sibling is None:
                    parent_fiber.child = fiber
                else:
                    previous_sibling.sibling = fiber
                break
            previous_sibling = current_child
            current_child = current_child.sibling
    reconciler._fiber_nodes[fiber.component_id] = fiber
    return fiber


def _complete_fiber_boundary(
    reconciler: _Reconciler,
    fiber: HookFiber,
    *,
    complete: Callable[[HookFiber], HookFiber],
) -> HookFiber:
    completed_fiber = complete(fiber)
    _finalize_completed_fiber_boundary(reconciler, fiber, completed_fiber)
    reconciler.pop_current_fiber()
    return completed_fiber


def _perform_immediate_structural_fiber_work(
    reconciler: _Reconciler,
    parent_fiber: HookFiber | None,
    fiber: HookFiber,
    *,
    work: Callable[[HookFiber], None],
) -> HookFiber:
    structural_fiber = _begin_structural_fiber(reconciler, parent_fiber, fiber)
    try:
        work(structural_fiber)
    finally:
        _end_structural_fiber(reconciler, structural_fiber)
    return structural_fiber


def _run_structural_fiber_work(
    reconciler: _Reconciler,
    parent_fiber: HookFiber | None,
    fiber: HookFiber,
    *,
    work: Callable[[HookFiber], int],
) -> int:
    structural_fiber = _begin_structural_fiber(reconciler, parent_fiber, fiber)
    try:
        return work(structural_fiber)
    except WorkYield as yielded:
        raise WorkYield(
            lambda: _run_structural_fiber_work(
                reconciler,
                parent_fiber,
                fiber,
                work=lambda _fiber: yielded.continuation(),
            )
        )
    finally:
        _end_structural_fiber(reconciler, structural_fiber)


def _run_function_fiber_work(
    reconciler: _Reconciler,
    parent_fiber: HookFiber | None,
    fiber: HookFiber,
    *,
    work: Callable[[HookFiber], int],
) -> int:
    function_fiber = _begin_function_fiber(reconciler, parent_fiber, fiber)
    try:
        return work(function_fiber)
    except WorkYield as yielded:
        raise WorkYield(
            lambda: _run_function_fiber_work(
                reconciler,
                parent_fiber,
                fiber,
                work=lambda _fiber: yielded.continuation(),
            )
        )
    except BaseException:
        unwindInterruptedWork(function_fiber)
        raise
    finally:
        _end_function_fiber(reconciler, function_fiber)


# Metadata Helpers

def _append_boundary_devtools_node(
    reconciler: _Reconciler,
    *,
    node_id: str,
    parent_id: str,
    display_name: str,
    element_type: str,
    key: str | None,
    is_error_boundary: bool,
) -> str:
    return appendDevtoolsNode(
        reconciler,
        node_id=node_id,
        parent_id=parent_id,
        display_name=display_name,
        element_type=element_type,
        key=key,
        is_error_boundary=is_error_boundary,
    )


def _build_boundary_inspection_payload(
    reconciler: _Reconciler,
    *,
    node_id: str,
    element_type: str,
    key: str | None,
    props: dict[str, Any] | None = None,
    hooks: list[dict[str, Any]] | None = None,
    can_edit_hooks: bool | None = None,
    can_edit_function_props: bool | None = None,
    can_toggle_suspense: bool | None = None,
    is_suspended: bool | None = None,
    nearest_suspense_boundary_id: str | None = None,
    source: Any = None,
    stack: Any = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "node_id": node_id,
        "element_type": element_type,
        "key": key,
        "can_toggle_error": bool(reconciler._error_boundary_stack),
        "can_toggle_suspense": (
            can_toggle_suspense
            if can_toggle_suspense is not None
            else bool(reconciler._suspense_boundary_stack)
        ),
        "nearest_error_boundary_id": (
            reconciler._error_boundary_stack[-1][0] if reconciler._error_boundary_stack else None
        ),
        "nearest_suspense_boundary_id": (
            nearest_suspense_boundary_id
            if nearest_suspense_boundary_id is not None
            else (
                reconciler._suspense_boundary_stack[-1]
                if reconciler._suspense_boundary_stack
                else None
            )
        ),
        "owners": reconciler._serialize_owner_stack(),
        "source": source if source is not None else reconciler._get_current_owner_source(),
        "stack": (
            stack
            if stack is not None
            else reconciler._build_owner_stack(reconciler._owner_component_stack)
        ),
    }
    if props is not None:
        payload["props"] = props
    if hooks is not None:
        payload["hooks"] = hooks
    if can_edit_hooks is not None:
        payload["can_edit_hooks"] = can_edit_hooks
    if can_edit_function_props is not None:
        payload["can_edit_function_props"] = can_edit_function_props
    if is_suspended is not None:
        payload["is_suspended"] = is_suspended
    return payload


def _update_boundary_inspection(
    reconciler: _Reconciler,
    *,
    node_id: str,
    element_type: str,
    key: str | None,
    props: dict[str, Any] | None = None,
    hooks: list[dict[str, Any]] | None = None,
    can_edit_hooks: bool | None = None,
    can_edit_function_props: bool | None = None,
    can_toggle_suspense: bool | None = None,
    is_suspended: bool | None = None,
    nearest_suspense_boundary_id: str | None = None,
    source: Any = None,
    stack: Any = None,
    suspended_by: list[dict[str, Any]] | None = None,
) -> None:
    payload = _build_boundary_inspection_payload(
        reconciler,
        node_id=node_id,
        element_type=element_type,
        key=key,
        props=props,
        hooks=hooks,
        can_edit_hooks=can_edit_hooks,
        can_edit_function_props=can_edit_function_props,
        can_toggle_suspense=can_toggle_suspense,
        is_suspended=is_suspended,
        nearest_suspense_boundary_id=nearest_suspense_boundary_id,
        source=source,
        stack=stack,
    )
    if suspended_by is not None:
        payload["suspended_by"] = suspended_by
    reconciler._record_inspected_element(**payload)


# Boundary Builders

def _build_structural_fiber_boundary(
    reconciler: _Reconciler,
    *,
    component_id: str,
    tag: int,
    element_type: str,
    display_name: str,
    key: str | None,
    path: tuple[Any, ...],
    pending_props: dict[str, Any] | None,
    pending_children: tuple[Any, ...] | None,
    parent_fiber: HookFiber | None,
    devtools_parent_id: str,
    is_error_boundary: bool = False,
    inspected_props: dict[str, Any] | None = None,
    can_toggle_suspense: bool | None = None,
    is_suspended: bool | None = None,
    nearest_suspense_boundary_id: str | None = None,
) -> tuple[HookFiber, str]:
    fiber = _create_or_reuse_structural_fiber(
        reconciler,
        component_id=component_id,
        tag=tag,
        element_type=element_type,
        key=key,
        path=path,
        pending_props=pending_props,
        pending_children=pending_children,
        return_fiber=parent_fiber,
    )
    node_id = _append_boundary_devtools_node(
        reconciler,
        node_id=component_id,
        parent_id=devtools_parent_id,
        display_name=display_name,
        element_type=element_type,
        key=key,
        is_error_boundary=is_error_boundary,
    )
    reconciler._record_inspected_element(
        **_build_boundary_inspection_payload(
            reconciler,
            node_id=node_id,
            element_type=element_type,
            key=key,
            props=inspected_props,
            can_toggle_suspense=can_toggle_suspense,
            is_suspended=is_suspended,
            nearest_suspense_boundary_id=nearest_suspense_boundary_id,
        )
    )
    return (fiber, node_id)


def _build_function_fiber_boundary(
    reconciler: _Reconciler,
    *,
    component_id: str,
    display_name: str,
    key: str | None,
    path: tuple[Any, ...],
    pending_props: dict[str, Any],
    pending_children: tuple[Any, ...] | None,
    parent_fiber: HookFiber | None,
    devtools_parent_id: str,
) -> tuple[HookFiber, str]:
    node_id = _append_boundary_devtools_node(
        reconciler,
        node_id=component_id,
        parent_id=devtools_parent_id,
        display_name=display_name,
        element_type="function",
        key=key,
        is_error_boundary=False,
    )
    fiber = HookFiber(
        component_id=component_id,
        tag=FunctionComponent,
        element_type="function",
        key=key,
        path=path,
        pending_props=pending_props,
        pending_children=pending_children,
        return_fiber=parent_fiber,
    )
    current = _get_current_tree_fiber(reconciler, component_id)
    if current is not None:
        fiber.alternate = current
        current.alternate = fiber
        fiber.memoized_props = getattr(current, "memoized_props", None)
        fiber.memoized_children = getattr(current, "memoized_children", None)
        fiber.lanes = getattr(current, "lanes", NoLanes)
        fiber.child_lanes = getattr(current, "child_lanes", NoLanes)
        fiber.dependencies = list(getattr(current, "dependencies", []))
        fiber.runtime_source_deps = list(getattr(current, "runtime_source_deps", []))
    return (fiber, node_id)


# Perform Helpers

def _reconcile_text_child(
    reconciler: _Reconciler,
    vnode: str,
    parent: DOMElement,
    path: tuple[Any, ...],
    dom_index: int,
) -> int:
    host_context = reconciler._host_context_stack[-1]
    if not host_context.get("isInsideText", False):
        raise ValueError(
            f'Text string "{vnode[:20]}..." must be rendered inside <Text> component'
        )

    parent_fiber = reconciler._current_fiber
    text_fiber = _create_or_reuse_structural_fiber(
        reconciler,
        component_id=buildDevtoolsNodeID(reconciler, "#text", path, None),
        tag=HostText,
        element_type="text",
        key=None,
        path=path,
        pending_props={"nodeValue": vnode},
        pending_children=None,
        return_fiber=parent_fiber,
    )
    _perform_immediate_structural_fiber_work(
        reconciler,
        parent_fiber,
        text_fiber,
        work=lambda fiber: _perform_text_fiber_work(
            reconciler,
            fiber=fiber,
            parent=parent,
            text=vnode,
            dom_index=dom_index,
        ),
    )
    return dom_index + 1


def _perform_text_fiber_work(
    reconciler: _Reconciler,
    *,
    fiber: HookFiber,
    parent: DOMElement,
    text: str,
    dom_index: int,
) -> None:
    fiber.state_node = reconciler._reconcile_text_node(parent, text, dom_index)


# Structural Performers

def _reconcile_fragment_child(
    reconciler: _Reconciler,
    vnode: RenderableNode,
    parent: DOMElement,
    children: list[RenderableNode],
    path: tuple[Any, ...],
    dom_index: int,
    devtools_parent_id: str,
) -> int:
    from pyinkcli.packages.react_reconciler.ReactFiberBeginWork import beginFragmentWork

    return beginFragmentWork(
        reconciler,
        vnode,
        parent,
        children,
        path,
        dom_index,
        devtools_parent_id,
    )


def _perform_fragment_fiber_work(
    reconciler: _Reconciler,
    *,
    parent: DOMElement,
    children: list[RenderableNode],
    path: tuple[Any, ...],
    dom_index: int,
    fragment_id: str,
) -> int:
    return reconcileChildren(
        reconciler,
        parent,
        children,
        path,
        dom_index,
        fragment_id,
    )


def _reconcile_host_child(
    reconciler: _Reconciler,
    vnode: RenderableNode,
    parent: DOMElement,
    props: dict[str, Any],
    children: list[RenderableNode],
    path: tuple[Any, ...],
    dom_index: int,
    devtools_parent_id: str,
    *,
    actual_type: str,
) -> int:
    from pyinkcli.packages.react_reconciler.ReactFiberBeginWork import beginHostWork

    return beginHostWork(
        reconciler,
        vnode,
        parent,
        props,
        children,
        path,
        dom_index,
        devtools_parent_id,
        actual_type=actual_type,
    )


def _reconcile_suspense_child(
    reconciler: _Reconciler,
    vnode: RenderableNode,
    parent: DOMElement,
    props: dict[str, Any],
    children: list[RenderableNode],
    path: tuple[Any, ...],
    dom_index: int,
    devtools_parent_id: str,
) -> int:
    from pyinkcli.packages.react_reconciler.ReactFiberBeginWork import beginSuspenseWork

    return beginSuspenseWork(
        reconciler,
        vnode,
        parent,
        props,
        children,
        path,
        dom_index,
        devtools_parent_id,
    )


def _reconcile_suspense_fiber_children(
    reconciler: _Reconciler,
    vnode: RenderableNode,
    parent: DOMElement,
    props: dict[str, Any],
    children: list[RenderableNode],
    path: tuple[Any, ...],
    dom_index: int,
    suspense_id: str,
    fallback: RenderableNode | None,
) -> int:
    try:
        return reconcileChildren(
            reconciler,
            parent,
            children,
            path,
            dom_index,
            suspense_id,
        )
    except SuspendSignal as signal:
        current_lane = getattr(reconciler._devtools_container, "current_update_priority", 0)
        reconciler._render_suspended = True
        reconciler._suspended_lanes_this_render = (
            getattr(reconciler, "_suspended_lanes_this_render", 0)
            | laneToMask(current_lane)
        )
        return _run_suspense_fallback_work(
            reconciler,
            vnode=vnode,
            parent_fiber=reconciler._current_fiber,
            suspense_fiber=reconciler._current_fiber,
            parent=parent,
            props=props,
            fallback=fallback,
            path=path,
            dom_index=dom_index,
            suspense_id=suspense_id,
            suspended_by=createSuspendedThenableRecord(signal),
        )


def _run_suspense_fallback_work(
    reconciler: _Reconciler,
    *,
    vnode: RenderableNode,
    parent_fiber: HookFiber | None,
    suspense_fiber: HookFiber,
    parent: DOMElement,
    props: dict[str, Any],
    fallback: RenderableNode | None,
    path: tuple[Any, ...],
    dom_index: int,
    suspense_id: str,
    suspended_by: list[dict[str, Any]] | None = None,
) -> int:
    _update_boundary_inspection(
        reconciler,
        node_id=suspense_id,
        element_type="suspense",
        key=vnode.key,
        props=props,
        can_toggle_suspense=True,
        is_suspended=True,
        nearest_suspense_boundary_id=suspense_id,
        suspended_by=suspended_by,
    )
    if fallback is None:
        return dom_index
    reconciler._suspense_boundary_stack.append(suspense_id)
    try:
        return _run_structural_fiber_work(
            reconciler,
            parent_fiber,
            suspense_fiber,
            work=lambda _fiber: reconcileChild(
                reconciler,
                fallback,
                parent,
                path + ("fallback",),
                dom_index,
                suspense_id,
            ),
        )
    finally:
        reconciler._suspense_boundary_stack.pop()


def _reconcile_host_fiber_children(
    reconciler: _Reconciler,
    dom_node: DOMElement,
    children: list[RenderableNode],
    path: tuple[Any, ...],
    host_node_id: str,
) -> int:
    next_child_index = reconcileChildren(
        reconciler,
        dom_node,
        children,
        path,
        0,
        host_node_id,
    )
    reconciler._remove_extra_children(dom_node, next_child_index)
    return 1


def _perform_host_fiber_work(
    reconciler: _Reconciler,
    *,
    vnode: RenderableNode,
    parent: DOMElement,
    props: dict[str, Any],
    children: list[RenderableNode],
    path: tuple[Any, ...],
    dom_index: int,
    actual_type: str,
    host_node_id: str,
) -> int:
    dom_node = reconciler._reconcile_element_node(
        parent,
        actual_type,
        props,
        children,
        path,
        dom_index,
        vnode.key,
    )
    current_fiber = reconciler._current_fiber
    if current_fiber is not None:
        current_fiber.state_node = dom_node
    if reconciler._next_devtools_host_instance_ids is not None:
        reconciler._next_devtools_host_instance_ids[id(dom_node)] = host_node_id

    new_host_context = getChildHostContext(reconciler._host_context_stack[-1], actual_type)
    reconciler._host_context_stack.append(new_host_context)
    try:
        return dom_index + _reconcile_host_fiber_children(
            reconciler,
            dom_node,
            children,
            path,
            host_node_id,
        )
    finally:
        reconciler._host_context_stack.pop()


def _reconcile_class_child(
    reconciler: _Reconciler,
    vnode: RenderableNode,
    node_type: Any,
    parent: DOMElement,
    props: dict[str, Any],
    children: list[RenderableNode],
    path: tuple[Any, ...],
    dom_index: int,
    devtools_parent_id: str,
    *,
    component_id: str,
    display_name: str,
    owner_entry: dict[str, Any],
) -> int:
    from pyinkcli.packages.react_reconciler.ReactFiberBeginWork import beginClassComponent

    return beginClassComponent(
        reconciler,
        vnode,
        node_type,
        parent,
        props,
        children,
        path,
        dom_index,
        devtools_parent_id,
        component_id=component_id,
        display_name=display_name,
        owner_entry=owner_entry,
    )


def _perform_class_fiber_work(
    reconciler: _Reconciler,
    *,
    vnode: RenderableNode,
    node_type: Any,
    parent: DOMElement,
    props: dict[str, Any],
    children: list[RenderableNode],
    path: tuple[Any, ...],
    dom_index: int,
    component_id: str,
    owner_entry: dict[str, Any],
) -> int:
    return reconciler._reconcile_class_component(
        component_type=node_type,
        component_id=component_id,
        props=props,
        children=children,
        parent=parent,
        path=path,
        dom_index=dom_index,
        devtools_parent_id=component_id,
        vnode_key=vnode.key,
        owner_entry=owner_entry,
    )


def _reconcile_function_child(
    reconciler: _Reconciler,
    vnode: RenderableNode,
    node_type: Any,
    parent: DOMElement,
    props: dict[str, Any],
    children: list[RenderableNode],
    path: tuple[Any, ...],
    dom_index: int,
    devtools_parent_id: str,
    *,
    component_id: str,
    display_name: str,
    component_source: Any,
    owner_entry: dict[str, Any],
) -> int:
    from pyinkcli.packages.react_reconciler.ReactFiberBeginWork import beginFunctionComponent

    return beginFunctionComponent(
        reconciler,
        vnode,
        node_type,
        parent,
        props,
        children,
        path,
        dom_index,
        devtools_parent_id,
        component_id=component_id,
        display_name=display_name,
        component_source=component_source,
        owner_entry=owner_entry,
    )


def _perform_function_fiber_work(
    reconciler: _Reconciler,
    vnode: RenderableNode,
    node_type: Any,
    parent: DOMElement,
    props: dict[str, Any],
    children: list[RenderableNode],
    path: tuple[Any, ...],
    dom_index: int,
    component_id: str,
    function_node_id: str,
    component_source: Any,
    owner_entry: dict[str, Any],
) -> int:
    rendered = renderWithHooks(
        reconciler._current_fiber,
        node_type,
        *children,
        **props,
    )
    _update_boundary_inspection(
        reconciler,
        node_id=function_node_id,
        element_type="function",
        key=vnode.key,
        props=props,
        hooks=getHookStateSnapshot(component_id),
        can_edit_hooks=True,
        can_edit_function_props=True,
        source=component_source,
        stack=reconciler._build_owner_stack(
            reconciler._owner_component_stack,
            current_entry=owner_entry,
        ),
    )
    reconciler._owner_component_stack.append(owner_entry)
    try:
        return reconcileChild(
            reconciler,
            rendered,
            parent,
            path,
            dom_index,
            component_id,
        )
    finally:
        reconciler._owner_component_stack.pop()


# Component Dispatch

def _reconcile_component_child(
    reconciler: _Reconciler,
    vnode: RenderableNode,
    node_type: Any,
    parent: DOMElement,
    props: dict[str, Any],
    children: list[RenderableNode],
    path: tuple[Any, ...],
    dom_index: int,
    devtools_parent_id: str,
) -> int:
    component_id = reconciler._get_component_instance_id(node_type, vnode, path)
    props = reconciler._get_effective_props(component_id, props)
    display_name = reconciler._get_component_display_name(node_type)
    component_source = reconciler._get_source_for_target(node_type, display_name)
    owner_entry = {
        "id": component_id,
        "displayName": display_name,
        "elementType": "class" if _is_component_class(node_type) else "function",
        "key": vnode.key,
        "source": component_source,
    }
    if _is_component_class(node_type):
        return _reconcile_class_child(
            reconciler,
            vnode,
            node_type,
            parent,
            props,
            children,
            path,
            dom_index,
            devtools_parent_id,
            component_id=component_id,
            display_name=display_name,
            owner_entry=owner_entry,
        )
    return _reconcile_function_child(
        reconciler,
        vnode,
        node_type,
        parent,
        props,
        children,
        path,
        dom_index,
        devtools_parent_id,
        component_id=component_id,
        display_name=display_name,
        component_source=component_source,
        owner_entry=owner_entry,
    )


def buildDevtoolsNodeID(
    _reconciler: _Reconciler,
    display_name: str,
    path: tuple[Any, ...],
    key: str | None,
) -> str:
    path_value = ".".join(str(part) for part in path)
    key_value = key or ""
    return f"{display_name}:{path_value}:{key_value}"


def appendDevtoolsNode(
    reconciler: _Reconciler,
    *,
    node_id: str,
    parent_id: str,
    display_name: str,
    element_type: str,
    key: str | None,
    is_error_boundary: bool,
) -> str:
    snapshot = reconciler._next_devtools_tree_snapshot
    if snapshot is None:
        return node_id
    nodes = snapshot["nodes"]
    for existing in nodes:
        if existing["id"] == node_id:
            return node_id
    nodes.append(
        {
            "id": node_id,
            "parentID": parent_id,
            "displayName": display_name,
            "elementType": element_type,
            "key": key,
            "isErrorBoundary": is_error_boundary,
        }
    )
    return node_id


def getChildPathToken(
    _reconciler: _Reconciler,
    child: RenderableNode,
    index: int,
) -> Any:
    if isElement(child) and child.key is not None:
        return f"key:{child.key}"
    return index


def getElementName(
    _reconciler: _Reconciler,
    node_type: Any,
) -> str | None:
    if isinstance(node_type, str):
        type_map = {
            "Box": "ink-box",
            "Text": "ink-text",
            "ink-box": "ink-box",
            "ink-text": "ink-text",
        }
        return type_map.get(node_type, node_type)
    return None


__all__ = [
    "appendDevtoolsNode",
    "buildDevtoolsNodeID",
    "getChildPathToken",
    "getElementName",
    "reconcileChild",
    "reconcileChildren",
]
