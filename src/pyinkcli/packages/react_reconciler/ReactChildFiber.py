"""Child reconciliation helpers aligned with ReactChildFiber responsibilities."""

from __future__ import annotations

from contextlib import ExitStack
from typing import TYPE_CHECKING, Any, Optional

from pyinkcli._component_runtime import _Fragment, _is_component_class, isElement, is_component, renderComponent
from pyinkcli._suspense_runtime import SuspendSignal
from pyinkcli.hooks._runtime import _begin_component_render, _end_component_render, _get_hook_state_snapshot
from pyinkcli.packages.react_reconciler.ReactFiberHostContext import getChildHostContext

if TYPE_CHECKING:
    from pyinkcli.component import RenderableNode
    from pyinkcli.packages.ink.dom import DOMElement
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler


def reconcileChildren(
    reconciler: "_Reconciler",
    parent: "DOMElement",
    children: list["RenderableNode"],
    path: tuple[Any, ...],
    dom_index: int,
    devtools_parent_id: str,
) -> int:
    for index, child in enumerate(children):
        child_path = path + (getChildPathToken(reconciler, child, index),)
        dom_index = reconcileChild(
            reconciler,
            child,
            parent,
            child_path,
            dom_index,
            devtools_parent_id,
        )
    return dom_index


def reconcileChild(
    reconciler: "_Reconciler",
    vnode: "RenderableNode",
    parent: "DOMElement",
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
        host_context = reconciler._host_context_stack[-1]
        if not host_context.get("isInsideText", False):
            raise ValueError(
                f'Text string "{vnode[:20]}..." must be rendered inside <Text> component'
            )

        reconciler._reconcile_text_node(parent, vnode, dom_index)
        return dom_index + 1

    node_type = vnode.type
    props = dict(vnode.props)
    children = list(vnode.children)

    if node_type == "__ink-suspense__":
        suspense_id = appendDevtoolsNode(
            reconciler,
            node_id=buildDevtoolsNodeID(reconciler, "Suspense", path, vnode.key),
            parent_id=devtools_parent_id,
            display_name="Suspense",
            element_type="suspense",
            key=vnode.key,
            is_error_boundary=False,
        )
        reconciler._record_inspected_element(
            node_id=suspense_id,
            element_type="suspense",
            key=vnode.key,
            props=props,
            can_toggle_error=bool(reconciler._error_boundary_stack),
            can_toggle_suspense=True,
            is_suspended=False,
            nearest_error_boundary_id=(
                reconciler._error_boundary_stack[-1][0] if reconciler._error_boundary_stack else None
            ),
            nearest_suspense_boundary_id=suspense_id,
            owners=reconciler._serialize_owner_stack(),
            source=reconciler._get_current_owner_source(),
            stack=reconciler._build_owner_stack(reconciler._owner_component_stack),
        )
        if suspense_id in reconciler._devtools_forced_suspense_boundaries:
            reconciler._record_inspected_element(
                node_id=suspense_id,
                element_type="suspense",
                key=vnode.key,
                props=props,
                can_toggle_error=bool(reconciler._error_boundary_stack),
                can_toggle_suspense=True,
                is_suspended=True,
                nearest_error_boundary_id=(
                    reconciler._error_boundary_stack[-1][0] if reconciler._error_boundary_stack else None
                ),
                nearest_suspense_boundary_id=suspense_id,
                owners=reconciler._serialize_owner_stack(),
                source=reconciler._get_current_owner_source(),
                stack=reconciler._build_owner_stack(reconciler._owner_component_stack),
            )
            fallback = props.get("fallback")
            if fallback is None:
                return dom_index
            reconciler._suspense_boundary_stack.append(suspense_id)
            try:
                return reconcileChild(
                    reconciler,
                    fallback,
                    parent,
                    path + ("fallback",),
                    dom_index,
                    suspense_id,
                )
            finally:
                reconciler._suspense_boundary_stack.pop()
        fallback = props.get("fallback")
        reconciler._suspense_boundary_stack.append(suspense_id)
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
            reconciler._record_inspected_element(
                node_id=suspense_id,
                element_type="suspense",
                key=vnode.key,
                props=props,
                can_toggle_error=bool(reconciler._error_boundary_stack),
                can_toggle_suspense=True,
                is_suspended=True,
                nearest_error_boundary_id=(
                    reconciler._error_boundary_stack[-1][0] if reconciler._error_boundary_stack else None
                ),
                nearest_suspense_boundary_id=suspense_id,
                owners=reconciler._serialize_owner_stack(),
                source=reconciler._get_current_owner_source(),
                stack=reconciler._build_owner_stack(reconciler._owner_component_stack),
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
            if fallback is None:
                return dom_index
            return reconcileChild(
                reconciler,
                fallback,
                parent,
                path + ("fallback",),
                dom_index,
                suspense_id,
            )
        finally:
            reconciler._suspense_boundary_stack.pop()

    if is_component(node_type):
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
            appendDevtoolsNode(
                reconciler,
                node_id=component_id,
                parent_id=devtools_parent_id,
                display_name=display_name,
                element_type="class",
                key=vnode.key,
                is_error_boundary=reconciler._is_component_type_error_boundary(node_type),
            )
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
        appendDevtoolsNode(
            reconciler,
            node_id=component_id,
            parent_id=devtools_parent_id,
            display_name=display_name,
            element_type="function",
            key=vnode.key,
            is_error_boundary=False,
        )
        _begin_component_render(component_id)
        try:
            rendered = renderComponent(node_type, *children, **props)
        finally:
            _end_component_render()
        reconciler._record_inspected_element(
            node_id=component_id,
            element_type="function",
            key=vnode.key,
            props=props,
            hooks=_get_hook_state_snapshot(component_id),
            can_edit_hooks=True,
            can_edit_function_props=True,
            can_toggle_error=bool(reconciler._error_boundary_stack),
            can_toggle_suspense=bool(reconciler._suspense_boundary_stack),
            nearest_error_boundary_id=(
                reconciler._error_boundary_stack[-1][0] if reconciler._error_boundary_stack else None
            ),
            nearest_suspense_boundary_id=(
                reconciler._suspense_boundary_stack[-1] if reconciler._suspense_boundary_stack else None
            ),
            owners=reconciler._serialize_owner_stack(),
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

    if node_type is _Fragment or node_type == "Fragment":
        fragment_id = appendDevtoolsNode(
            reconciler,
            node_id=buildDevtoolsNodeID(reconciler, "Fragment", path, vnode.key),
            parent_id=devtools_parent_id,
            display_name="Fragment",
            element_type="fragment",
            key=vnode.key,
            is_error_boundary=False,
        )
        reconciler._record_inspected_element(
            node_id=fragment_id,
            element_type="fragment",
            key=vnode.key,
            can_toggle_error=bool(reconciler._error_boundary_stack),
            can_toggle_suspense=bool(reconciler._suspense_boundary_stack),
            nearest_error_boundary_id=(
                reconciler._error_boundary_stack[-1][0] if reconciler._error_boundary_stack else None
            ),
            nearest_suspense_boundary_id=(
                reconciler._suspense_boundary_stack[-1] if reconciler._suspense_boundary_stack else None
            ),
            owners=reconciler._serialize_owner_stack(),
            source=reconciler._get_current_owner_source(),
            stack=reconciler._build_owner_stack(reconciler._owner_component_stack),
        )
        return reconcileChildren(reconciler, parent, children, path, dom_index, fragment_id)

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

    host_node_id = appendDevtoolsNode(
        reconciler,
        node_id=buildDevtoolsNodeID(reconciler, actual_type, path, vnode.key),
        parent_id=devtools_parent_id,
        display_name=actual_type,
        element_type="host",
        key=vnode.key,
        is_error_boundary=False,
    )
    reconciler._record_inspected_element(
        node_id=host_node_id,
        element_type="host",
        key=vnode.key,
        props=props,
        can_toggle_error=bool(reconciler._error_boundary_stack),
        can_toggle_suspense=bool(reconciler._suspense_boundary_stack),
        nearest_error_boundary_id=(
            reconciler._error_boundary_stack[-1][0] if reconciler._error_boundary_stack else None
        ),
        nearest_suspense_boundary_id=(
            reconciler._suspense_boundary_stack[-1] if reconciler._suspense_boundary_stack else None
        ),
        owners=reconciler._serialize_owner_stack(),
        source=reconciler._get_current_owner_source(),
        stack=reconciler._build_owner_stack(reconciler._owner_component_stack),
    )

    dom_node = reconciler._reconcile_element_node(
        parent,
        actual_type,
        props,
        children,
        path,
        dom_index,
        vnode.key,
    )
    if reconciler._next_devtools_host_instance_ids is not None:
        reconciler._next_devtools_host_instance_ids[id(dom_node)] = host_node_id

    new_host_context = getChildHostContext(reconciler._host_context_stack[-1], actual_type)
    reconciler._host_context_stack.append(new_host_context)
    try:
        next_child_index = reconcileChildren(
            reconciler,
            dom_node,
            children,
            path,
            0,
            host_node_id,
        )
        reconciler._remove_extra_children(dom_node, next_child_index)
    finally:
        reconciler._host_context_stack.pop()

    return dom_index + 1


def buildDevtoolsNodeID(
    _reconciler: "_Reconciler",
    display_name: str,
    path: tuple[Any, ...],
    key: Optional[str],
) -> str:
    path_value = ".".join(str(part) for part in path)
    key_value = key or ""
    return f"{display_name}:{path_value}:{key_value}"


def appendDevtoolsNode(
    reconciler: "_Reconciler",
    *,
    node_id: str,
    parent_id: str,
    display_name: str,
    element_type: str,
    key: Optional[str],
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
    _reconciler: "_Reconciler",
    child: "RenderableNode",
    index: int,
) -> Any:
    if isElement(child) and child.key is not None:
        return f"key:{child.key}"
    return index


def getElementName(
    _reconciler: "_Reconciler",
    node_type: Any,
) -> Optional[str]:
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
