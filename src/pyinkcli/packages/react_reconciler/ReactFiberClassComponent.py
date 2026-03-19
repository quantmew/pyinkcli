"""Class component and error boundary helpers aligned with reconciler responsibilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from pyinkcli._component_runtime import (
    _Component,
    _create_component_instance,
    _merge_component_props,
    renderComponent,
)
from pyinkcli.hooks._runtime import _batched_updates_runtime

if TYPE_CHECKING:
    from pyinkcli.component import RenderableNode
    from pyinkcli.packages.react_dom.host import DOMElement
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler


def reconcileClassComponent(
    reconciler: "_Reconciler",
    *,
    component_type: type[_Component],
    component_id: str,
    props: dict[str, Any],
    children: list["RenderableNode"],
    parent: "DOMElement",
    path: tuple[Any, ...],
    dom_index: int,
    devtools_parent_id: str,
    vnode_key: Optional[str],
    owner_entry: dict[str, Any],
) -> int:
    instance, is_new_instance, previous_props, previous_state = getOrCreateClassComponentInstance(
        reconciler,
        component_type,
        component_id,
        tuple(children),
        props,
    )
    instance._nearest_error_boundary = (
        reconciler._error_boundary_stack[-1][2] if reconciler._error_boundary_stack else None
    )
    should_update = True
    if (
        not is_new_instance
        and callable(getattr(instance, "shouldComponentUpdate", None))
    ):
        should_update = bool(
            instance.shouldComponentUpdate(
                dict(instance.props),
                dict(instance.state),
            )
        )

    is_error_boundary = isErrorBoundary(reconciler, component_type, instance)
    if component_id in reconciler._devtools_forced_error_boundaries and is_error_boundary:
        applyErrorBoundaryState(
            reconciler,
            component_type,
            instance,
            reconciler._create_devtools_forced_error(),
        )

    if should_update or instance._last_rendered_node is None:
        rendered = instance.render()
        instance._last_rendered_node = rendered
    else:
        rendered = instance._last_rendered_node

    reconciler._record_inspected_element(
        node_id=component_id,
        element_type="class",
        key=vnode_key,
        props=dict(instance.props),
        state=dict(instance.state),
        context=None,
        can_edit_hooks=False,
        can_edit_function_props=False,
        can_toggle_error=is_error_boundary or bool(reconciler._error_boundary_stack),
        is_errored=component_id in reconciler._devtools_forced_error_boundaries
        or bool(instance.state.get("error")),
        can_toggle_suspense=bool(reconciler._suspense_boundary_stack),
        nearest_error_boundary_id=(
            component_id
            if is_error_boundary
            else (
                reconciler._error_boundary_stack[-1][0]
                if reconciler._error_boundary_stack
                else None
            )
        ),
        nearest_suspense_boundary_id=(
            reconciler._suspense_boundary_stack[-1]
            if reconciler._suspense_boundary_stack
            else None
        ),
        owners=reconciler._serialize_owner_stack(),
        source=owner_entry.get("source"),
        stack=reconciler._build_owner_stack(
            reconciler._owner_component_stack,
            current_entry=owner_entry,
        ),
    )

    scheduleClassComponentCommitCallback(
        reconciler,
        instance,
        is_new_instance=is_new_instance,
        should_update=should_update,
        previous_props=previous_props,
        previous_state=previous_state,
    )

    reconciler._owner_component_stack.append(owner_entry)
    if not is_error_boundary:
        try:
            return reconciler._reconcile_child(
                rendered,
                parent,
                path,
                dom_index,
                devtools_parent_id,
            )
        finally:
            reconciler._owner_component_stack.pop()

    reconciler._error_boundary_stack.append((component_id, component_type, instance))
    try:
        return reconciler._reconcile_child(
            rendered,
            parent,
            path,
            dom_index,
            devtools_parent_id,
        )
    except Exception as error:
        fallback = renderErrorBoundaryFallback(
            reconciler,
            component_type,
            instance,
            error,
        )
        reconciler._record_inspected_element(
            node_id=component_id,
            element_type="class",
            key=vnode_key,
            props=dict(instance.props),
            state=dict(instance.state),
            context=None,
            can_edit_hooks=False,
            can_edit_function_props=False,
            can_toggle_error=True,
            is_errored=bool(instance.state.get("error")),
            can_toggle_suspense=bool(reconciler._suspense_boundary_stack),
            nearest_error_boundary_id=component_id,
            nearest_suspense_boundary_id=(
                reconciler._suspense_boundary_stack[-1]
                if reconciler._suspense_boundary_stack
                else None
            ),
            owners=reconciler._serialize_owner_stack(),
            source=owner_entry.get("source"),
            stack=reconciler._build_owner_stack(
                reconciler._owner_component_stack,
                current_entry=owner_entry,
            ),
        )
        return reconciler._reconcile_child(
            fallback,
            parent,
            path,
            dom_index,
            devtools_parent_id,
        )
    finally:
        reconciler._error_boundary_stack.pop()
        reconciler._owner_component_stack.pop()


def getOrCreateClassComponentInstance(
    reconciler: "_Reconciler",
    component_type: type[_Component],
    component_id: str,
    children: tuple["RenderableNode", ...],
    props: dict[str, Any],
) -> tuple[_Component, bool, dict[str, Any], dict[str, Any]]:
    reconciler._visited_class_component_ids.add(component_id)
    instance = reconciler._class_component_instances.get(component_id)
    merged_props = _merge_component_props(children, props)

    if instance is None or not isinstance(instance, component_type):
        instance = _create_component_instance(component_type, children, props)
        reconciler._class_component_instances[component_id] = instance
        return (instance, True, {}, {})

    previous_props = dict(instance.props)
    previous_state = (
        dict(instance._pending_previous_state)
        if instance._pending_previous_state is not None
        else dict(instance.state)
    )
    instance._pending_previous_state = None
    instance.props = merged_props
    instance._is_unmounted = False
    return (instance, False, previous_props, previous_state)


def scheduleClassComponentCommitCallback(
    reconciler: "_Reconciler",
    instance: _Component,
    *,
    is_new_instance: bool,
    should_update: bool,
    previous_props: dict[str, Any],
    previous_state: dict[str, Any],
) -> None:
    if is_new_instance:
        if callable(getattr(instance, "componentDidMount", None)):
            reconciler._pending_class_component_commit_callbacks.append(
                (instance, lambda: invokeComponentDidMount(reconciler, instance))
            )
        else:
            instance._is_mounted = True
        return

    if (
        not is_new_instance
        and should_update
        and callable(getattr(instance, "componentDidUpdate", None))
    ):
        reconciler._pending_class_component_commit_callbacks.append(
            (
                instance,
                lambda: invokeComponentDidUpdate(
                    reconciler,
                    instance,
                    previous_props,
                    previous_state,
                ),
            )
        )


def invokeComponentDidMount(
    _reconciler: "_Reconciler",
    instance: _Component,
) -> None:
    instance._is_mounted = True
    instance.componentDidMount()


def invokeComponentDidUpdate(
    _reconciler: "_Reconciler",
    instance: _Component,
    previous_props: dict[str, Any],
    previous_state: dict[str, Any],
) -> None:
    instance._is_mounted = True
    instance.componentDidUpdate(previous_props, previous_state)


def flushClassComponentCommitCallbacks(
    reconciler: "_Reconciler",
) -> bool:
    callbacks = reconciler._pending_class_component_commit_callbacks[:]
    reconciler._pending_class_component_commit_callbacks.clear()
    if not callbacks:
        return reconciler._commit_phase_recovery_requested

    unhandled_error: Optional[Exception] = None

    def run_callbacks() -> None:
        nonlocal unhandled_error
        for instance, callback in callbacks:
            try:
                callback()
            except Exception as error:
                if captureCommitPhaseError(reconciler, instance, error):
                    continue
                if unhandled_error is None:
                    unhandled_error = error

    _batched_updates_runtime(run_callbacks)
    if unhandled_error is not None:
        raise unhandled_error
    return reconciler._commit_phase_recovery_requested


def cleanupClassComponentInstances(reconciler: "_Reconciler") -> None:
    component_ids = list(reconciler._class_component_instances.keys())
    for component_id in component_ids:
        instance = reconciler._class_component_instances.pop(component_id, None)
        if instance is None:
            continue
        unmountClassComponentInstance(reconciler, instance)


def disposeStaleClassComponentInstances(reconciler: "_Reconciler") -> None:
    stale_component_ids = [
        component_id
        for component_id in reconciler._class_component_instances
        if component_id not in reconciler._visited_class_component_ids
    ]
    for component_id in stale_component_ids:
        instance = reconciler._class_component_instances.pop(component_id, None)
        if instance is None:
            continue
        unmountClassComponentInstance(reconciler, instance)


def unmountClassComponentInstance(
    reconciler: "_Reconciler",
    instance: _Component,
) -> None:
    instance._is_unmounted = True
    if not callable(getattr(instance, "componentWillUnmount", None)):
        return
    try:
        instance.componentWillUnmount()
    except Exception as error:
        if not captureCommitPhaseError(reconciler, instance, error):
            raise


def captureCommitPhaseError(
    reconciler: "_Reconciler",
    instance: _Component,
    error: Exception,
) -> bool:
    boundary = getattr(instance, "_nearest_error_boundary", None)
    if boundary is None or getattr(boundary, "_is_unmounted", False):
        return False

    derived_state = getattr(type(boundary), "getDerivedStateFromError", None)
    if callable(derived_state):
        next_state = derived_state(error)
        if isinstance(next_state, dict):
            boundary.state.update(next_state)
            boundary._state_version += 1

    reconciler._deferred_component_did_catch.append((boundary, error))
    reconciler._commit_phase_recovery_requested = True
    return True


def isErrorBoundary(
    _reconciler: "_Reconciler",
    component_type: type[_Component],
    instance: _Component,
) -> bool:
    return callable(getattr(component_type, "getDerivedStateFromError", None)) or callable(
        getattr(instance, "componentDidCatch", None)
    )


def renderErrorBoundaryFallback(
    reconciler: "_Reconciler",
    component_type: type[_Component],
    instance: _Component,
    error: Exception,
) -> "RenderableNode":
    applyErrorBoundaryState(reconciler, component_type, instance, error)

    if callable(getattr(instance, "componentDidCatch", None)):
        reconciler._pending_component_did_catch.append((instance, error))

    return renderComponent(instance)


def applyErrorBoundaryState(
    _reconciler: "_Reconciler",
    component_type: type[_Component],
    instance: _Component,
    error: Exception,
) -> None:
    derived_state = getattr(component_type, "getDerivedStateFromError", None)
    if not callable(derived_state):
        return
    if instance._pending_previous_state is None:
        instance._pending_previous_state = dict(instance.state)
    next_state = derived_state(error)
    if isinstance(next_state, dict):
        instance.state.update(next_state)
        instance._state_version += 1


def flushComponentDidCatchCallbacks(
    reconciler: "_Reconciler",
    *,
    include_deferred: bool,
) -> None:
    pending_callbacks = reconciler._pending_component_did_catch[:]
    reconciler._pending_component_did_catch.clear()
    if include_deferred:
        pending_callbacks.extend(reconciler._deferred_component_did_catch)
        reconciler._deferred_component_did_catch.clear()
    for instance, error in pending_callbacks:
        try:
            instance.componentDidCatch(error)
        except Exception:
            pass


__all__ = [
    "applyErrorBoundaryState",
    "captureCommitPhaseError",
    "cleanupClassComponentInstances",
    "disposeStaleClassComponentInstances",
    "flushClassComponentCommitCallbacks",
    "flushComponentDidCatchCallbacks",
    "getOrCreateClassComponentInstance",
    "invokeComponentDidMount",
    "invokeComponentDidUpdate",
    "isErrorBoundary",
    "reconcileClassComponent",
    "renderErrorBoundaryFallback",
    "scheduleClassComponentCommitCallback",
    "unmountClassComponentInstance",
]
