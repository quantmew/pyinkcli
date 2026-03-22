"""Begin-work helpers aligned with ReactFiberBeginWork responsibilities."""

from __future__ import annotations

from contextlib import ExitStack

from pyinkcli._component_runtime import (
    _Fragment,
    _coalesce_component_children,
    _is_component_class,
    createElement,
    is_component,
)
from pyinkcli.packages.react_reconciler.ReactFiberLane import NoLanes
from pyinkcli.packages.react_reconciler.ReactFiberNewContext import (
    checkIfContextChanged,
    popProvider,
    pushProvider,
    readContext,
)
from pyinkcli.packages.react_reconciler.ReactFiberRuntimeSources import (
    checkIfRuntimeSourcesChanged,
    recordRuntimeSourceDependency,
)
from pyinkcli.packages.react_reconciler.ReactFiberThenable import (
    createSuspendedThenableRecord,
)
from pyinkcli.packages.react_reconciler.ReactWorkTags import (
    HostComponent,
    HostText,
)

didReceiveUpdate: bool = False


def markWorkInProgressReceivedUpdate() -> None:
    global didReceiveUpdate
    didReceiveUpdate = True


def checkIfWorkInProgressReceivedUpdate() -> bool:
    return didReceiveUpdate


def resetWorkInProgressReceivedUpdate() -> None:
    global didReceiveUpdate
    didReceiveUpdate = False


def _iter_fiber_subtree(root, seen: set[int] | None = None):
    if root is None:
        return
    if seen is None:
        seen = set()
    root_id = id(root)
    if root_id in seen:
        return
    seen.add(root_id)
    yield root
    child = getattr(root, "child", None)
    while child is not None:
        yield from _iter_fiber_subtree(child, seen)
        child = getattr(child, "sibling", None)


def _count_host_descendants(fiber) -> int:
    count = 0
    for current in _iter_fiber_subtree(fiber):
        if getattr(current, "tag", None) in (HostComponent, HostText):
            count += 1
    return count


def _subtree_contains_pending_reveal(current_fiber) -> bool:
    for fiber in _iter_fiber_subtree(current_fiber):
        if bool(getattr(fiber, "is_suspended", False)):
            return True
        if bool(getattr(fiber, "contains_suspended_fibers", False)):
            return True
        path = getattr(fiber, "path", ()) or ()
        if "fallback" in path:
            return True
    return False


def _has_active_devtools_forcing(reconciler) -> bool:
    return bool(
        getattr(reconciler, "_devtools_prop_overrides", None)
        or getattr(reconciler, "_devtools_forced_error_boundaries", None)
        or getattr(reconciler, "_devtools_forced_suspense_boundaries", None)
    )


def _track_component_runtime_sources(
    reconciler,
    fiber,
    node_type,
) -> None:
    runtime_sources = getattr(node_type, "__ink_runtime_sources__", None)
    if not runtime_sources:
        return
    for source in runtime_sources:
        recordRuntimeSourceDependency(reconciler, fiber, str(source))


def _can_bailout_function_component(
    reconciler,
    current_fiber,
    node_type,
    pending_props,
    pending_children,
) -> bool:
    if _has_active_devtools_forcing(reconciler):
        return False
    if reconciler._suspense_boundary_stack:
        return False
    if not _has_bailout_safe_hook_structure(
        current_fiber,
        node_type=node_type,
    ):
        return False
    return _can_bailout(
        reconciler,
        current_fiber,
        pending_props,
        pending_children,
        check_context=True,
    )


def _reparent_bailed_out_children(parent_fiber) -> None:
    child = getattr(parent_fiber, "child", None)
    while child is not None:
        child.return_fiber = parent_fiber
        child = getattr(child, "sibling", None)


def _copy_devtools_subtree_for_bailout(reconciler, current_fiber) -> None:
    snapshot = reconciler._next_devtools_tree_snapshot
    if snapshot is not None:
        next_nodes = snapshot["nodes"]
        existing_ids = {node["id"] for node in next_nodes}
        previous_nodes = {
            node["id"]: node for node in reconciler._devtools_tree_snapshot.get("nodes", [])
        }
        for fiber in _iter_fiber_subtree(current_fiber):
            node_id = getattr(fiber, "component_id", None)
            if node_id is None or node_id in existing_ids:
                continue
            previous = previous_nodes.get(node_id)
            if previous is None:
                continue
            next_nodes.append(dict(previous))
            existing_ids.add(node_id)

    target_maps = (
        ("_devtools_inspected_elements", "_next_devtools_inspected_elements"),
        (
            "_devtools_inspected_element_fingerprints",
            "_next_devtools_inspected_element_fingerprints",
        ),
        ("_devtools_effective_props", "_next_devtools_effective_props"),
    )
    for source_name, target_name in target_maps:
        source = getattr(reconciler, source_name, None)
        target = getattr(reconciler, target_name, None)
        if not isinstance(source, dict) or not isinstance(target, dict):
            continue
        for fiber in _iter_fiber_subtree(current_fiber):
            node_id = getattr(fiber, "component_id", None)
            if node_id in source and node_id not in target:
                target[node_id] = source[node_id]

    host_instance_ids = getattr(reconciler, "_next_devtools_host_instance_ids", None)
    if isinstance(host_instance_ids, dict):
        for fiber in _iter_fiber_subtree(current_fiber):
            state_node = getattr(fiber, "state_node", None)
            node_id = getattr(fiber, "component_id", None)
            if state_node is not None and node_id is not None:
                host_instance_ids[id(state_node)] = node_id


def _can_bailout(
    reconciler,
    current_fiber,
    pending_props,
    pending_children,
    *,
    check_context: bool = False,
) -> bool:
    if current_fiber is None:
        return False
    if getattr(current_fiber, "memoized_props", None) != pending_props:
        return False
    if getattr(current_fiber, "memoized_children", None) != pending_children:
        return False
    if getattr(current_fiber, "lanes", NoLanes) != NoLanes:
        return False
    if getattr(current_fiber, "child_lanes", NoLanes) != NoLanes:
        return False
    if _subtree_contains_pending_reveal(current_fiber):
        return False
    if checkIfRuntimeSourcesChanged(
        reconciler,
        getattr(current_fiber, "runtime_source_deps", None),
    ):
        return False
    if check_context and checkIfContextChanged(getattr(current_fiber, "dependencies", None)):
        return False
    return True


def _has_bailout_safe_hook_structure(current_fiber, *, node_type) -> bool:
    runtime_sources = {
        str(source)
        for source, _version in getattr(current_fiber, "runtime_source_deps", ())
    }
    allowed_internal_runtime_sources = {
        "router.location",
        "router.navigation",
        "cursor",
        "static_output",
    }
    module_name = getattr(node_type, "__module__", "")
    is_internal_component = isinstance(module_name, str) and module_name.startswith("pyinkcli.")
    if is_internal_component and runtime_sources - allowed_internal_runtime_sources:
        return False

    hook = getattr(current_fiber, "hook_head", None)
    while hook is not None:
        kind = getattr(hook, "kind", "Unknown")
        if kind in {"State", "Reducer"}:
            return False
        if kind == "Effect" and getattr(hook, "deps", None) is None:
            return False
        if kind in {"Memo", "Callback"} and getattr(hook, "memoized_deps", None) is None:
            return False
        if kind not in {"Ref", "Effect", "Memo", "Callback", "Unknown"}:
            return False
        hook = getattr(hook, "next", None)
    return True


def _bailout_on_already_finished_work(
    reconciler,
    work_in_progress,
    dom_index: int,
    *,
    host_boundary: bool = False,
) -> int:
    current = getattr(work_in_progress, "alternate", None)
    if current is None:
        return dom_index
    work_in_progress.child = current.child
    work_in_progress.state_node = current.state_node
    work_in_progress.memoized_props = current.memoized_props
    work_in_progress.pending_children = getattr(current, "pending_children", None)
    work_in_progress.memoized_children = getattr(current, "memoized_children", None)
    work_in_progress.memoized_state = getattr(current, "memoized_state", None)
    work_in_progress.dependencies = list(getattr(current, "dependencies", []))
    work_in_progress.runtime_source_deps = list(getattr(current, "runtime_source_deps", []))
    work_in_progress.lanes = NoLanes
    work_in_progress.child_lanes = getattr(current, "child_lanes", NoLanes)
    work_in_progress.subtree_flags = getattr(current, "subtree_flags", 0)
    work_in_progress.flags = 0
    work_in_progress.did_bailout = True
    _reparent_bailed_out_children(work_in_progress)
    _copy_devtools_subtree_for_bailout(reconciler, current)
    if host_boundary:
        return dom_index + 1
    return dom_index + _count_host_descendants(current)


def beginTextWork(
    reconciler,
    text: str,
    parent,
    path,
    dom_index: int,
):
    from pyinkcli.packages.react_reconciler.ReactChildFiber import (
        _create_or_reuse_structural_fiber,
        _perform_immediate_structural_fiber_work,
        buildDevtoolsNodeID,
    )

    host_context = reconciler._host_context_stack[-1]
    if not host_context.get("isInsideText", False):
        raise ValueError(
            f'Text string "{text[:20]}..." must be rendered inside <Text> component'
        )

    parent_fiber = reconciler._current_fiber
    text_fiber = _create_or_reuse_structural_fiber(
        reconciler,
        component_id=buildDevtoolsNodeID(reconciler, "#text", path, None),
        tag=6,
        element_type="text",
        key=None,
        path=path,
        pending_props={"nodeValue": text},
        pending_children=None,
        return_fiber=parent_fiber,
    )
    _perform_immediate_structural_fiber_work(
        reconciler,
        parent_fiber,
        text_fiber,
        work=lambda fiber: setattr(
            fiber,
            "state_node",
            reconciler._reconcile_text_node(parent, text, dom_index),
        ),
    )
    return dom_index + 1


def beginFunctionComponent(
    reconciler,
    element,
    node_type,
    parent,
    props,
    children,
    path,
    dom_index: int,
    devtools_parent_id: str,
    *,
    component_id: str,
    display_name: str,
    component_source,
    owner_entry,
):
    from pyinkcli.packages.react_reconciler.ReactChildFiber import (
        _build_function_fiber_boundary,
        _run_function_fiber_work,
        _update_boundary_inspection,
        getHookStateSnapshot,
        reconcileChild,
    )
    from pyinkcli.packages.react_reconciler.ReactFiberHooks import renderWithHooks

    parent_fiber = reconciler._current_fiber
    fiber, function_node_id = _build_function_fiber_boundary(
        reconciler,
        component_id=component_id,
        display_name=display_name,
        key=element.key,
        path=path,
        pending_props=props,
        pending_children=tuple(children),
        parent_fiber=parent_fiber,
        devtools_parent_id=devtools_parent_id,
    )
    _track_component_runtime_sources(reconciler, fiber, node_type)
    current_fiber = getattr(fiber, "alternate", None)
    if _can_bailout_function_component(
        reconciler,
        current_fiber,
        node_type,
        props,
        tuple(children),
    ):
        return _bailout_on_already_finished_work(reconciler, fiber, dom_index)
    return _run_function_fiber_work(
        reconciler,
        parent_fiber,
        fiber,
        work=lambda _fiber: _perform_function_component_work(
            reconciler,
            element,
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
            render_with_hooks=renderWithHooks,
            update_boundary_inspection=_update_boundary_inspection,
            get_hook_state_snapshot=getHookStateSnapshot,
            reconcile_child=reconcileChild,
        ),
    )


def _perform_function_component_work(
    reconciler,
    element,
    node_type,
    parent,
    props,
    children,
    path,
    dom_index: int,
    component_id: str,
    function_node_id: str,
    component_source,
    owner_entry,
    *,
    render_with_hooks,
    update_boundary_inspection,
    get_hook_state_snapshot,
    reconcile_child,
):
    rendered = render_with_hooks(
        reconciler._current_fiber,
        node_type,
        *children,
        **props,
    )
    update_boundary_inspection(
        reconciler,
        node_id=function_node_id,
        element_type="function",
        key=element.key,
        props=props,
        hooks=get_hook_state_snapshot(component_id),
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
        return reconcile_child(
            reconciler,
            rendered,
            parent,
            path,
            dom_index,
            component_id,
        )
    finally:
        reconciler._owner_component_stack.pop()


def beginClassComponent(
    reconciler,
    element,
    node_type,
    parent,
    props,
    children,
    path,
    dom_index: int,
    devtools_parent_id: str,
    *,
    component_id: str,
    display_name: str,
    owner_entry,
):
    from pyinkcli.packages.react_reconciler.ReactChildFiber import (
        _build_structural_fiber_boundary,
        _run_structural_fiber_work,
    )

    parent_fiber = reconciler._current_fiber
    class_fiber, _class_node_id = _build_structural_fiber_boundary(
        reconciler,
        component_id=component_id,
        tag=1,
        element_type="class",
        display_name=display_name,
        key=element.key,
        path=path,
        pending_props=props,
        pending_children=tuple(children),
        parent_fiber=parent_fiber,
        devtools_parent_id=devtools_parent_id,
        is_error_boundary=reconciler._is_component_type_error_boundary(node_type),
        inspected_props=props,
    )
    return _run_structural_fiber_work(
        reconciler,
        parent_fiber,
        class_fiber,
        work=lambda _fiber: reconciler._reconcile_class_component(
            component_type=node_type,
            component_id=component_id,
            props=props,
            children=children,
            parent=parent,
            path=path,
            dom_index=dom_index,
            devtools_parent_id=component_id,
            vnode_key=element.key,
            owner_entry=owner_entry,
        ),
    )


def beginFragmentWork(
    reconciler,
    element,
    parent,
    children,
    path,
    dom_index: int,
    devtools_parent_id: str,
):
    from pyinkcli.packages.react_reconciler.ReactChildFiber import (
        _build_structural_fiber_boundary,
        _run_structural_fiber_work,
        buildDevtoolsNodeID,
        reconcileChildren,
    )

    parent_fiber = reconciler._current_fiber
    fragment_fiber, fragment_id = _build_structural_fiber_boundary(
        reconciler,
        component_id=buildDevtoolsNodeID(reconciler, "Fragment", path, element.key),
        tag=7,
        element_type="fragment",
        display_name="Fragment",
        key=element.key,
        path=path,
        pending_props=None,
        pending_children=tuple(children),
        parent_fiber=parent_fiber,
        devtools_parent_id=devtools_parent_id,
    )
    if (
        not _has_active_devtools_forcing(reconciler)
        and not reconciler._suspense_boundary_stack
        and _can_bailout(
            reconciler,
            getattr(fragment_fiber, "alternate", None),
            None,
            tuple(children),
        )
    ):
        return _run_structural_fiber_work(
            reconciler,
            parent_fiber,
            fragment_fiber,
            work=lambda _fiber: _bailout_on_already_finished_work(
                reconciler,
                _fiber,
                dom_index,
            ),
        )
    return _run_structural_fiber_work(
        reconciler,
        parent_fiber,
        fragment_fiber,
        work=lambda _fiber: reconcileChildren(
            reconciler,
            parent,
            children,
            path,
            dom_index,
            fragment_id,
        ),
    )


def beginSuspenseWork(
    reconciler,
    element,
    parent,
    props,
    children,
    path,
    dom_index: int,
    devtools_parent_id: str,
):
    from pyinkcli.packages.react_reconciler.ReactChildFiber import (
        _build_structural_fiber_boundary,
        _run_structural_fiber_work,
        _update_boundary_inspection,
        buildDevtoolsNodeID,
        laneToMask,
        reconcileChild,
        reconcileChildren,
    )

    parent_fiber = reconciler._current_fiber
    suspense_id = buildDevtoolsNodeID(reconciler, "Suspense", path, element.key)
    suspense_fiber, suspense_id = _build_structural_fiber_boundary(
        reconciler,
        component_id=suspense_id,
        tag=13,
        element_type="suspense",
        display_name="Suspense",
        key=element.key,
        path=path,
        pending_props=props,
        pending_children=tuple(children),
        parent_fiber=parent_fiber,
        devtools_parent_id=devtools_parent_id,
        inspected_props=props,
        can_toggle_suspense=True,
        is_suspended=False,
        nearest_suspense_boundary_id=suspense_id,
    )
    fallback = props.get("fallback")
    if suspense_id in reconciler._devtools_forced_suspense_boundaries:
        return _run_suspense_fallback_work(
            reconciler,
            element,
            parent_fiber,
            suspense_fiber,
            parent,
            props,
            fallback,
            path,
            dom_index,
            suspense_id,
            update_boundary_inspection=_update_boundary_inspection,
            reconcile_child=reconcileChild,
            run_structural_fiber_work=_run_structural_fiber_work,
        )

    reconciler._suspense_boundary_stack.append(suspense_id)
    try:
        return _run_structural_fiber_work(
            reconciler,
            parent_fiber,
            suspense_fiber,
            work=lambda _fiber: _reconcile_suspense_children(
                reconciler,
                element,
                parent,
                props,
                children,
                path,
                dom_index,
                suspense_id,
                fallback,
                reconcile_children=reconcileChildren,
                reconcile_child=reconcileChild,
                update_boundary_inspection=_update_boundary_inspection,
                run_structural_fiber_work=_run_structural_fiber_work,
                lane_to_mask=laneToMask,
            ),
        )
    finally:
        reconciler._suspense_boundary_stack.pop()


def _reconcile_suspense_children(
    reconciler,
    element,
    parent,
    props,
    children,
    path,
    dom_index: int,
    suspense_id: str,
    fallback,
    *,
    reconcile_children,
    reconcile_child,
    update_boundary_inspection,
    run_structural_fiber_work,
    lane_to_mask,
):
    from pyinkcli._suspense_runtime import SuspendSignal

    try:
        return reconcile_children(
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
            | lane_to_mask(current_lane)
        )
        return _run_suspense_fallback_work(
            reconciler,
            element,
            reconciler._current_fiber,
            reconciler._current_fiber,
            parent,
            props=props,
            fallback=fallback,
            path=path,
            dom_index=dom_index,
            suspense_id=suspense_id,
            suspended_by=createSuspendedThenableRecord(signal),
            update_boundary_inspection=update_boundary_inspection,
            reconcile_child=reconcile_child,
            run_structural_fiber_work=run_structural_fiber_work,
        )


def _run_suspense_fallback_work(
    reconciler,
    element,
    parent_fiber,
    suspense_fiber,
    parent,
    props,
    fallback,
    path,
    dom_index: int,
    suspense_id: str,
    suspended_by=None,
    *,
    update_boundary_inspection,
    reconcile_child,
    run_structural_fiber_work,
):
    update_boundary_inspection(
        reconciler,
        node_id=suspense_id,
        element_type="suspense",
        key=element.key,
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
        return run_structural_fiber_work(
            reconciler,
            parent_fiber,
            suspense_fiber,
            work=lambda _fiber: reconcile_child(
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


def beginHostWork(
    reconciler,
    element,
    parent,
    props,
    children,
    path,
    dom_index: int,
    devtools_parent_id: str,
    *,
    actual_type: str,
):
    from pyinkcli.packages.react_reconciler.ReactChildFiber import (
        _build_structural_fiber_boundary,
        _run_structural_fiber_work,
        getChildHostContext,
        reconcileChildren,
    )

    parent_fiber = reconciler._current_fiber
    host_fiber, host_node_id = _build_structural_fiber_boundary(
        reconciler,
        component_id=reconciler._get_component_instance_id(actual_type, element, path),
        tag=5,
        element_type="host",
        display_name=actual_type,
        key=element.key,
        path=path,
        pending_props=props,
        pending_children=tuple(children),
        parent_fiber=parent_fiber,
        devtools_parent_id=devtools_parent_id,
        inspected_props=props,
    )
    return _run_structural_fiber_work(
        reconciler,
        parent_fiber,
        host_fiber,
        work=lambda _fiber: _perform_host_work(
            reconciler,
            element,
            parent,
            props,
            children,
            path,
            dom_index,
            actual_type,
            host_node_id,
            get_child_host_context=getChildHostContext,
            reconcile_children=reconcileChildren,
        ),
    )


def _perform_host_work(
    reconciler,
    element,
    parent,
    props,
    children,
    path,
    dom_index: int,
    actual_type: str,
    host_node_id: str,
    *,
    get_child_host_context,
    reconcile_children,
):
    dom_node = reconciler._reconcile_element_node(
        parent,
        actual_type,
        props,
        children,
        path,
        dom_index,
        element.key,
    )
    current_fiber = reconciler._current_fiber
    if current_fiber is not None:
        current_fiber.state_node = dom_node
    if reconciler._next_devtools_host_instance_ids is not None:
        reconciler._next_devtools_host_instance_ids[id(dom_node)] = host_node_id

    new_host_context = get_child_host_context(reconciler._host_context_stack[-1], actual_type)
    reconciler._host_context_stack.append(new_host_context)
    try:
        next_child_index = reconcile_children(
            reconciler,
            dom_node,
            children,
            path,
            0,
            host_node_id,
        )
        reconciler._remove_extra_children(dom_node, next_child_index)
        return dom_index + 1
    finally:
        reconciler._host_context_stack.pop()


def beginWork(
    reconciler,
    current: object | None,
    workInProgress: object,
    element,
    parent,
    path,
    dom_index: int,
    devtools_parent_id: str,
):
    del current, workInProgress

    if element is None:
        return dom_index

    context_manager_factories = getattr(element, "context_manager_factories", None)
    if context_manager_factories is not None:
        with ExitStack() as stack:
            for factory in context_manager_factories:
                stack.enter_context(factory())
            return beginWork(
                reconciler,
                None,
                None,
                element.node,
                parent,
                path,
                dom_index,
                devtools_parent_id,
            )

    from pyinkcli.packages.react_reconciler.ReactChildFiber import getElementName

    if isinstance(element, str):
        return beginTextWork(reconciler, element, parent, path, dom_index)

    node_type = element.type
    props = dict(element.props)
    children = list(element.children)

    if getattr(node_type, "__ink_react_lazy__", False):
        resolved_type = node_type._init(node_type._payload)
        return beginWork(
            reconciler,
            None,
            None,
            createElement(resolved_type, *children, key=element.key, **props),
            parent,
            path,
            dom_index,
            devtools_parent_id,
        )

    if getattr(node_type, "__ink_react_provider__", False):
        child = _coalesce_component_children(tuple(children))
        pushProvider(reconciler, node_type._context, props.get("value"))
        try:
            return beginWork(
                reconciler,
                None,
                None,
                child,
                parent,
                path,
                dom_index,
                devtools_parent_id,
            )
        finally:
            popProvider(reconciler, node_type._context)

    if getattr(node_type, "__ink_react_consumer__", False):
        render_child = children[0] if children and callable(children[0]) else None
        rendered = render_child(readContext(node_type._context)) if render_child is not None else None
        return beginWork(
            reconciler,
            None,
            None,
            rendered,
            parent,
            path,
            dom_index,
            devtools_parent_id,
        )

    if getattr(node_type, "__ink_react_memo__", False):
        node_type = node_type.type

    if getattr(element.type, "__ink_react_forward_ref__", False):
        component_type = element.type
        forwarded_ref = props.pop("ref", None)
        component_id = reconciler._get_component_instance_id(component_type, element, path)
        props = reconciler._get_effective_props(component_id, props)
        display_name = reconciler._get_component_display_name(component_type)
        component_source = reconciler._get_source_for_target(component_type, display_name)
        owner_entry = {
            "id": component_id,
            "displayName": display_name,
            "elementType": "forwardRef",
            "key": element.key,
            "source": component_source,
        }

        def render_forward_ref(*render_children, **render_props):
            merged_props = dict(render_props)
            if "children" not in merged_props:
                merged_props["children"] = _coalesce_component_children(render_children)
            return component_type.render(merged_props, forwarded_ref)

        return beginFunctionComponent(
            reconciler,
            element,
            render_forward_ref,
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

    if node_type == "__ink-suspense__":
        return beginSuspenseWork(
            reconciler,
            element,
            parent=parent,
            props=props,
            children=children,
            path=path,
            dom_index=dom_index,
            devtools_parent_id=devtools_parent_id,
        )

    if is_component(node_type):
        component_id = reconciler._get_component_instance_id(node_type, element, path)
        props = reconciler._get_effective_props(component_id, props)
        display_name = reconciler._get_component_display_name(node_type)
        component_source = reconciler._get_source_for_target(node_type, display_name)
        owner_entry = {
            "id": component_id,
            "displayName": display_name,
            "elementType": "class" if _is_component_class(node_type) else "function",
            "key": element.key,
            "source": component_source,
        }
        if _is_component_class(node_type):
            return beginClassComponent(
                reconciler,
                element,
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
        return beginFunctionComponent(
            reconciler,
            element,
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

    if node_type is _Fragment or node_type == "Fragment":
        return beginFragmentWork(
            reconciler,
            element,
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

    return beginHostWork(
        reconciler,
        element,
        parent,
        props,
        children,
        path,
        dom_index,
        devtools_parent_id,
        actual_type=actual_type,
    )


__all__ = [
    "beginWork",
    "beginClassComponent",
    "beginFragmentWork",
    "beginFunctionComponent",
    "beginHostWork",
    "beginSuspenseWork",
    "beginTextWork",
    "checkIfWorkInProgressReceivedUpdate",
    "didReceiveUpdate",
    "markWorkInProgressReceivedUpdate",
    "resetWorkInProgressReceivedUpdate",
]
