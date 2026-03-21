"""Child reconciliation helpers aligned with ReactChildFiber responsibilities."""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pyinkcli._component_runtime import (
    _Fragment,
    _is_component_class,
    is_component,
    isElement,
    renderComponent,
)
from pyinkcli._suspense_runtime import SuspendSignal
from pyinkcli.hooks._runtime import (
    HookFiber,
    _begin_component_render,
    _commit_completed_fiber,
    _end_component_render,
    _get_hook_state_snapshot,
    _set_current_hook_fiber,
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
    if vnode is None:
        return dom_index

    context_manager_factories = getattr(vnode, "context_manager_factories", None)
    if context_manager_factories is not None:
        with ExitStack() as stack:
            for factory in context_manager_factories:
                stack.enter_context(factory())
            return reconcileChild(
                reconciler,
                vnode.node,
                parent,
                path,
                dom_index,
                devtools_parent_id,
            )

    if isinstance(vnode, str):
        return _reconcile_text_child(reconciler, vnode, parent, path, dom_index)

    node_type = vnode.type
    props = dict(vnode.props)
    children = list(vnode.children)

    if node_type == "__ink-suspense__":
        return _reconcile_suspense_child(
            reconciler,
            props=props,
            children=children,
            vnode=vnode,
            parent=parent,
            path=path,
            dom_index=dom_index,
            devtools_parent_id=devtools_parent_id,
        )

    if is_component(node_type):
        return _reconcile_component_child(
            reconciler,
            vnode,
            node_type,
            parent,
            props,
            children,
            path,
            dom_index,
            devtools_parent_id,
        )

    if node_type is _Fragment or node_type == "Fragment":
        return _reconcile_fragment_child(
            reconciler,
            vnode,
            parent,
            children,
            path,
            dom_index,
            devtools_parent_id,
        )

    element_name = getElementName(reconciler, node_type)
    if element_name is None:
        return dom_index

    host_context = reconciler._host_context_stack[-1]
    is_inside_text = host_context.get("isInsideText", False)

    if is_inside_text and element_name == "ink-box":
        raise ValueError("<Box> can't be nested inside <Text> component")

    actual_type = element_name
    if element_name == "ink-text" and is_inside_text:
        actual_type = "ink-virtual-text"

    return _reconcile_host_child(
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
    return_fiber: HookFiber | None,
) -> HookFiber:
    current = reconciler._fiber_nodes.get(component_id)
    if current is None or getattr(current, "tag", None) != tag:
        return HookFiber(
            component_id=component_id,
            tag=tag,
            element_type=element_type,
            key=key,
            path=path,
            pending_props=pending_props,
            memoized_props=None,
            return_fiber=return_fiber,
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
            return_fiber=return_fiber,
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
        work_in_progress.return_fiber = return_fiber

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
    _set_current_hook_fiber(None)
    return _end_component_render() or fiber


def _prepare_structural_fiber_boundary(fiber: HookFiber) -> HookFiber:
    return fiber


def _prepare_function_fiber_boundary(fiber: HookFiber) -> HookFiber:
    return _begin_component_render(fiber)


def _enter_structural_fiber_boundary(fiber: HookFiber) -> None:
    return None


def _enter_function_fiber_boundary(fiber: HookFiber) -> None:
    _set_current_hook_fiber(fiber)


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
    fiber: HookFiber,
) -> HookFiber:
    reconciler._fiber_nodes[fiber.component_id] = fiber
    return fiber


def _complete_fiber_boundary(
    reconciler: _Reconciler,
    fiber: HookFiber,
    *,
    complete: Callable[[HookFiber], HookFiber],
) -> HookFiber:
    completed_fiber = complete(fiber)
    _finalize_completed_fiber_boundary(reconciler, completed_fiber)
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
        return_fiber=parent_fiber,
    )
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
    parent_fiber = reconciler._current_fiber
    fragment_fiber, fragment_id = _build_structural_fiber_boundary(
        reconciler,
        component_id=buildDevtoolsNodeID(reconciler, "Fragment", path, vnode.key),
        tag=Fragment,
        element_type="fragment",
        display_name="Fragment",
        key=vnode.key,
        path=path,
        pending_props=None,
        parent_fiber=parent_fiber,
        devtools_parent_id=devtools_parent_id,
    )
    return _run_structural_fiber_work(
        reconciler,
        parent_fiber,
        fragment_fiber,
        work=lambda _fiber: _perform_fragment_fiber_work(
            reconciler,
            parent=parent,
            children=children,
            path=path,
            dom_index=dom_index,
            fragment_id=fragment_id,
        ),
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
    parent_fiber = reconciler._current_fiber
    host_fiber, host_node_id = _build_structural_fiber_boundary(
        reconciler,
        component_id=buildDevtoolsNodeID(reconciler, actual_type, path, vnode.key),
        tag=HostComponent,
        element_type="host",
        display_name=actual_type,
        key=vnode.key,
        path=path,
        pending_props=props,
        parent_fiber=parent_fiber,
        devtools_parent_id=devtools_parent_id,
        inspected_props=props,
    )
    return _run_structural_fiber_work(
        reconciler,
        parent_fiber,
        host_fiber,
        work=lambda _fiber: _perform_host_fiber_work(
            reconciler,
            vnode=vnode,
            parent=parent,
            props=props,
            children=children,
            path=path,
            dom_index=dom_index,
            actual_type=actual_type,
            host_node_id=host_node_id,
        ),
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
    parent_fiber = reconciler._current_fiber
    suspense_fiber, suspense_id = _build_structural_fiber_boundary(
        reconciler,
        component_id=buildDevtoolsNodeID(reconciler, "Suspense", path, vnode.key),
        tag=SuspenseComponent,
        element_type="suspense",
        display_name="Suspense",
        key=vnode.key,
        path=path,
        pending_props=props,
        parent_fiber=parent_fiber,
        devtools_parent_id=devtools_parent_id,
        inspected_props=props,
        can_toggle_suspense=True,
        is_suspended=False,
        nearest_suspense_boundary_id=buildDevtoolsNodeID(reconciler, "Suspense", path, vnode.key),
    )

    fallback = props.get("fallback")
    if suspense_id in reconciler._devtools_forced_suspense_boundaries:
        return _run_suspense_fallback_work(
            reconciler,
            vnode=vnode,
            parent_fiber=parent_fiber,
            suspense_fiber=suspense_fiber,
            parent=parent,
            props=props,
            fallback=fallback,
            path=path,
            dom_index=dom_index,
            suspense_id=suspense_id,
        )

    reconciler._suspense_boundary_stack.append(suspense_id)
    try:
        return _run_structural_fiber_work(
            reconciler,
            parent_fiber,
            suspense_fiber,
            work=lambda _fiber: _reconcile_suspense_fiber_children(
                reconciler,
                vnode,
                parent,
                props,
                children,
                path,
                dom_index,
                suspense_id,
                fallback,
            ),
        )
    finally:
        reconciler._suspense_boundary_stack.pop()


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
            suspended_by=[
                {
                    "name": "SuspendSignal",
                    "awaited": {
                        "value": {
                            "resource": {
                                "key": repr(signal.key),
                            },
                            "message": str(signal),
                        }
                    },
                    "env": None,
                    "owner": None,
                    "stack": None,
                }
            ],
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
    parent_fiber = reconciler._current_fiber
    class_fiber, _class_node_id = _build_structural_fiber_boundary(
        reconciler,
        component_id=component_id,
        tag=ClassComponent,
        element_type="class",
        display_name=display_name,
        key=vnode.key,
        path=path,
        pending_props=props,
        parent_fiber=parent_fiber,
        devtools_parent_id=devtools_parent_id,
        is_error_boundary=reconciler._is_component_type_error_boundary(node_type),
        inspected_props=props,
    )
    return _run_structural_fiber_work(
        reconciler,
        parent_fiber,
        class_fiber,
        work=lambda _fiber: _perform_class_fiber_work(
            reconciler,
            vnode=vnode,
            node_type=node_type,
            parent=parent,
            props=props,
            children=children,
            path=path,
            dom_index=dom_index,
            component_id=component_id,
            owner_entry=owner_entry,
        ),
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
    parent_fiber = reconciler._current_fiber
    fiber, function_node_id = _build_function_fiber_boundary(
        reconciler,
        component_id=component_id,
        display_name=display_name,
        key=vnode.key,
        path=path,
        pending_props=props,
        parent_fiber=parent_fiber,
        devtools_parent_id=devtools_parent_id,
    )
    return _run_function_fiber_work(
        reconciler,
        parent_fiber,
        fiber,
        work=lambda function_fiber: _perform_function_fiber_work(
            reconciler,
            vnode,
            node_type,
            parent,
            props,
            children,
            path,
            dom_index,
            component_id,
            function_node_id,
            component_source,
            owner_entry,
        ),
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
    rendered = renderComponent(node_type, *children, **props)
    _update_boundary_inspection(
        reconciler,
        node_id=function_node_id,
        element_type="function",
        key=vnode.key,
        props=props,
        hooks=_get_hook_state_snapshot(component_id),
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
