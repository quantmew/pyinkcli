"""DevTools mutation and backend command helpers aligned with reconciler responsibilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyinkcli.hooks._runtime import (
    _delete_hook_state_path,
    _override_hook_state,
    _rename_hook_state_path,
)

if TYPE_CHECKING:
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler


def getDevtoolsMutableProps(
    reconciler: _Reconciler,
    node_id: str,
) -> dict[str, Any] | None:
    base = reconciler._devtools_prop_overrides.get(node_id)
    if base is None:
        base = reconciler._devtools_effective_props.get(node_id)
    if base is None:
        return None
    return reconciler._clone_inspected_value(base)


def recordDevtoolsBackendNotification(
    reconciler: _Reconciler,
    event: str,
    *,
    renderer_id: int | None = None,
    node_id: str | None = None,
    path: list[Any] | None = None,
    count: int | None = None,
    copied_value: str | None = None,
    global_key: str | None = None,
    suspended_set: list[Any] | None = None,
    normalized_suspended_set: list[Any] | None = None,
) -> None:
    entry: dict[str, Any] = {"event": event}
    if renderer_id is not None:
        entry["rendererID"] = renderer_id
    if node_id is not None:
        entry["id"] = node_id
    if path is not None:
        entry["path"] = list(path)
    if count is not None:
        entry["count"] = count
    if copied_value is not None:
        entry["copiedValue"] = copied_value
    if global_key is not None:
        entry["globalKey"] = global_key
    if suspended_set is not None:
        entry["suspendedSet"] = reconciler._clone_inspected_value(suspended_set)
    if normalized_suspended_set is not None:
        entry["normalizedSuspendedSet"] = reconciler._clone_inspected_value(normalized_suspended_set)
    reconciler._devtools_backend_notification_log.append(entry)


def overrideDevtoolsProps(
    reconciler: _Reconciler,
    node_id: str,
    path: list[Any],
    value: Any,
) -> bool:
    props = getDevtoolsMutableProps(reconciler, node_id)
    if props is None:
        return False
    reconciler._set_nested_value(props, path, value)
    reconciler._devtools_prop_overrides[node_id] = props
    return True


def overrideDevtoolsError(
    reconciler: _Reconciler,
    node_id: str,
    force_error: bool,
) -> bool:
    boundary_id = reconciler._devtools_nearest_error_boundary_by_node.get(node_id)
    if boundary_id is None:
        boundary_id = reconciler._find_nearest_tree_ancestor(
            node_id,
            predicate=lambda node: bool(node.get("isErrorBoundary")),
        )
    if boundary_id is None:
        return False

    instance = reconciler._class_component_instances.get(boundary_id)
    if instance is None:
        return False

    if force_error:
        if boundary_id not in reconciler._devtools_forced_error_boundaries:
            reconciler._devtools_forced_error_boundary_states[boundary_id] = (
                reconciler._clone_inspected_value(instance.state)
            )
        reconciler._devtools_forced_error_boundaries.add(boundary_id)
        reconciler._apply_error_boundary_state(
            type(instance),
            instance,
            reconciler._create_devtools_forced_error(),
        )
        return scheduleDevtoolsUpdate(reconciler, boundary_id)

    reconciler._devtools_forced_error_boundaries.discard(boundary_id)
    previous_state = reconciler._devtools_forced_error_boundary_states.pop(boundary_id, None)
    if previous_state is not None:
        if instance._pending_previous_state is None:
            instance._pending_previous_state = dict(instance.state)
        instance.state = reconciler._clone_inspected_value(previous_state)
        instance._state_version += 1
    return scheduleDevtoolsRetry(reconciler, boundary_id)


def overrideDevtoolsSuspense(
    reconciler: _Reconciler,
    node_id: str,
    force_fallback: bool,
) -> bool:
    suspense_id = reconciler._devtools_nearest_suspense_boundary_by_node.get(node_id)
    if suspense_id is None:
        suspense_id = reconciler._find_nearest_tree_ancestor(
            node_id,
            predicate=lambda node: node.get("elementType") == "suspense",
        )
    if suspense_id is None:
        return False

    if force_fallback:
        reconciler._devtools_forced_suspense_boundaries.add(suspense_id)
        return scheduleDevtoolsUpdate(reconciler, suspense_id)

    reconciler._devtools_forced_suspense_boundaries.discard(suspense_id)
    return scheduleDevtoolsRetry(reconciler, suspense_id)


def overrideDevtoolsSuspenseMilestone(
    reconciler: _Reconciler,
    suspended_set: list[str],
    renderer_id: int | None = None,
) -> bool:
    normalized_target: set[str] = set()
    for node_id in suspended_set:
        suspense_id = reconciler._devtools_nearest_suspense_boundary_by_node.get(node_id)
        if suspense_id is None:
            node = reconciler._get_tree_node(node_id)
            if node is not None and node.get("elementType") == "suspense":
                suspense_id = node_id
            else:
                suspense_id = reconciler._find_nearest_tree_ancestor(
                    node_id,
                    predicate=lambda candidate: candidate.get("elementType") == "suspense",
                )
        if suspense_id is not None:
            normalized_target.add(suspense_id)

    current_forced = set(reconciler._devtools_forced_suspense_boundaries)
    unsuspended = current_forced - normalized_target
    resuspended = False

    for suspense_id in normalized_target:
        if suspense_id in current_forced:
            unsuspended.discard(suspense_id)
            continue
        reconciler._devtools_forced_suspense_boundaries.add(suspense_id)
        scheduleDevtoolsUpdate(reconciler, suspense_id)
        resuspended = True

    for suspense_id in unsuspended:
        reconciler._devtools_forced_suspense_boundaries.discard(suspense_id)
        if not resuspended:
            scheduleDevtoolsRetry(reconciler, suspense_id)
        else:
            scheduleDevtoolsUpdate(reconciler, suspense_id)

    recordDevtoolsBackendNotification(
        reconciler,
        "overrideSuspenseMilestone",
        renderer_id=renderer_id,
        suspended_set=list(suspended_set),
        normalized_suspended_set=sorted(normalized_target),
    )
    return True


def deleteDevtoolsPropsPath(
    reconciler: _Reconciler,
    node_id: str,
    path: list[Any],
) -> bool:
    props = getDevtoolsMutableProps(reconciler, node_id)
    if props is None:
        return False
    if not reconciler._delete_nested_value(props, path):
        return False
    reconciler._devtools_prop_overrides[node_id] = props
    return True


def renameDevtoolsPropsPath(
    reconciler: _Reconciler,
    node_id: str,
    old_path: list[Any],
    new_path: list[Any],
) -> bool:
    props = getDevtoolsMutableProps(reconciler, node_id)
    if props is None:
        return False
    value, found = reconciler._pop_nested_value(props, old_path)
    if not found:
        return False
    reconciler._set_nested_value(props, new_path, value)
    reconciler._devtools_prop_overrides[node_id] = props
    return True


def overrideDevtoolsHookState(
    _reconciler: _Reconciler,
    node_id: str,
    path: list[Any],
    value: Any,
) -> bool:
    return _override_hook_state(node_id, path, value)


def deleteDevtoolsHookStatePath(
    _reconciler: _Reconciler,
    node_id: str,
    path: list[Any],
) -> bool:
    return _delete_hook_state_path(node_id, path)


def renameDevtoolsHookStatePath(
    _reconciler: _Reconciler,
    node_id: str,
    old_path: list[Any],
    new_path: list[Any],
) -> bool:
    return _rename_hook_state_path(node_id, old_path, new_path)


def overrideDevtoolsState(
    reconciler: _Reconciler,
    node_id: str,
    path: list[Any],
    value: Any,
) -> bool:
    instance = reconciler._class_component_instances.get(node_id)
    if instance is None:
        return False
    if not path:
        if not isinstance(value, dict):
            return False
        if instance._pending_previous_state is None:
            instance._pending_previous_state = dict(instance.state)
        instance.state = reconciler._clone_inspected_value(value)
        return True
    if instance._pending_previous_state is None:
        instance._pending_previous_state = dict(instance.state)
    return reconciler._set_nested_value(instance.state, path, value)


def deleteDevtoolsStatePath(
    reconciler: _Reconciler,
    node_id: str,
    path: list[Any],
) -> bool:
    instance = reconciler._class_component_instances.get(node_id)
    if instance is None or not path:
        return False
    if instance._pending_previous_state is None:
        instance._pending_previous_state = dict(instance.state)
    return reconciler._delete_nested_value(instance.state, path)


def renameDevtoolsStatePath(
    reconciler: _Reconciler,
    node_id: str,
    old_path: list[Any],
    new_path: list[Any],
) -> bool:
    instance = reconciler._class_component_instances.get(node_id)
    if instance is None or not old_path or not new_path:
        return False
    if instance._pending_previous_state is None:
        instance._pending_previous_state = dict(instance.state)
    value, found = reconciler._pop_nested_value(instance.state, old_path)
    if not found:
        return False
    return reconciler._set_nested_value(instance.state, new_path, value)


def overrideDevtoolsValueAtPath(
    reconciler: _Reconciler,
    value_type: str,
    node_id: str,
    hook_id: int | None,
    path: list[Any],
    value: Any,
) -> bool:
    if value_type == "props":
        return overrideDevtoolsProps(reconciler, node_id, path, value)
    if value_type == "hooks":
        hook_path = reconciler._normalize_hook_edit_path(hook_id, path)
        if hook_path is None:
            return False
        return overrideDevtoolsHookState(reconciler, node_id, hook_path, value)
    if value_type == "state":
        return overrideDevtoolsState(reconciler, node_id, path, value)
    return False


def deleteDevtoolsPath(
    reconciler: _Reconciler,
    value_type: str,
    node_id: str,
    hook_id: int | None,
    path: list[Any],
) -> bool:
    if value_type == "props":
        return deleteDevtoolsPropsPath(reconciler, node_id, path)
    if value_type == "hooks":
        hook_path = reconciler._normalize_hook_edit_path(hook_id, path)
        if hook_path is None:
            return False
        return deleteDevtoolsHookStatePath(reconciler, node_id, hook_path)
    if value_type == "state":
        return deleteDevtoolsStatePath(reconciler, node_id, path)
    return False


def renameDevtoolsPath(
    reconciler: _Reconciler,
    value_type: str,
    node_id: str,
    hook_id: int | None,
    old_path: list[Any],
    new_path: list[Any],
) -> bool:
    if value_type == "props":
        return renameDevtoolsPropsPath(reconciler, node_id, old_path, new_path)
    if value_type == "hooks":
        hook_old_path = reconciler._normalize_hook_edit_path(hook_id, old_path)
        hook_new_path = reconciler._normalize_hook_edit_path(hook_id, new_path)
        if hook_old_path is None or hook_new_path is None:
            return False
        return renameDevtoolsHookStatePath(reconciler, node_id, hook_old_path, hook_new_path)
    if value_type == "state":
        return renameDevtoolsStatePath(reconciler, node_id, old_path, new_path)
    return False


def scheduleDevtoolsUpdate(
    reconciler: _Reconciler,
    node_id: str,
) -> bool:
    if not reconciler._has_tree_node(node_id):
        return False
    if reconciler._devtools_container is None:
        return False
    reconciler.request_rerender(reconciler._devtools_container, priority="default")
    return True


def scheduleDevtoolsRetry(
    reconciler: _Reconciler,
    node_id: str,
) -> bool:
    if not reconciler._has_tree_node(node_id):
        return False
    if reconciler._devtools_container is None:
        return False
    reconciler.request_rerender(reconciler._devtools_container, priority="default")
    return True


def clearDevtoolsErrorsAndWarnings(
    reconciler: _Reconciler,
    renderer_id: int | None = None,
) -> bool:
    recordDevtoolsBackendNotification(
        reconciler,
        "clearErrorsAndWarnings",
        renderer_id=renderer_id,
    )
    return True


def clearDevtoolsErrorsForElement(
    reconciler: _Reconciler,
    id: str,
    renderer_id: int | None = None,
) -> bool:
    recordDevtoolsBackendNotification(
        reconciler,
        "clearErrorsForElementID",
        renderer_id=renderer_id,
        node_id=id,
    )
    return reconciler._has_tree_node(id)


def clearDevtoolsWarningsForElement(
    reconciler: _Reconciler,
    id: str,
    renderer_id: int | None = None,
) -> bool:
    recordDevtoolsBackendNotification(
        reconciler,
        "clearWarningsForElementID",
        renderer_id=renderer_id,
        node_id=id,
    )
    return reconciler._has_tree_node(id)


def copyDevtoolsElementPath(
    reconciler: _Reconciler,
    id: str,
    path: list[Any],
    renderer_id: int | None = None,
) -> str | None:
    from pyinkcli.packages.react_devtools_core.window_polyfill import installDevtoolsWindowPolyfill

    copied = reconciler.getSerializedElementValueByPath(id, path)
    reconciler._devtools_last_copied_value = copied
    recordDevtoolsBackendNotification(
        reconciler,
        "copyElementPath",
        renderer_id=renderer_id,
        node_id=id,
        path=path,
        copied_value=copied,
    )
    installDevtoolsWindowPolyfill()["__INK_DEVTOOLS_LAST_COPIED_VALUE__"] = copied
    return copied


def storeDevtoolsValueAsGlobal(
    reconciler: _Reconciler,
    id: str,
    path: list[Any],
    count: int,
    renderer_id: int | None = None,
) -> str | None:
    from pyinkcli.packages.react_devtools_core.window_polyfill import installDevtoolsWindowPolyfill

    global_key = f"$reactTemp{count}"
    value = reconciler.getElementValueByPath(id, path)
    reconciler._devtools_stored_globals[global_key] = value
    recordDevtoolsBackendNotification(
        reconciler,
        "storeAsGlobal",
        renderer_id=renderer_id,
        node_id=id,
        path=path,
        count=count,
        global_key=global_key,
    )
    global_scope = installDevtoolsWindowPolyfill()
    global_scope.setdefault("__INK_DEVTOOLS_STORED_GLOBALS__", {})[global_key] = value
    global_scope[global_key] = value
    return global_key


def getDevtoolsLastCopiedValue(
    reconciler: _Reconciler,
) -> str | None:
    return reconciler._devtools_last_copied_value


def getDevtoolsLastLoggedElement(
    reconciler: _Reconciler,
) -> dict[str, Any] | None:
    if reconciler._devtools_last_logged_element is None:
        return None
    return reconciler._clone_inspected_value(reconciler._devtools_last_logged_element)


def getDevtoolsTrackedPath(
    reconciler: _Reconciler,
) -> list[dict[str, Any]] | None:
    if reconciler._devtools_tracked_path is None:
        return None
    return reconciler._clone_inspected_value(reconciler._devtools_tracked_path)


def getDevtoolsStoredGlobals(
    reconciler: _Reconciler,
) -> dict[str, Any]:
    return reconciler._clone_inspected_value(reconciler._devtools_stored_globals)


def getDevtoolsBackendNotificationLog(
    reconciler: _Reconciler,
) -> list[dict[str, Any]]:
    return [
        {
            key: reconciler._clone_inspected_value(value)
            for key, value in entry.items()
        }
        for entry in reconciler._devtools_backend_notification_log
    ]


def logDevtoolsElementToConsole(
    reconciler: _Reconciler,
    id: str,
    renderer_id: int | None = None,
) -> bool:
    from pyinkcli.packages.react_devtools_core.window_polyfill import installDevtoolsWindowPolyfill

    element = reconciler._devtools_inspected_elements.get(id)
    if element is None:
        return False
    snapshot = reconciler._clone_inspected_value(element)
    reconciler._devtools_last_logged_element = snapshot
    recordDevtoolsBackendNotification(
        reconciler,
        "logElementToConsole",
        renderer_id=renderer_id,
        node_id=id,
    )
    installDevtoolsWindowPolyfill()["__INK_DEVTOOLS_LAST_LOGGED_ELEMENT__"] = snapshot
    return True


def setDevtoolsTrackedPath(
    reconciler: _Reconciler,
    path: list[dict[str, Any]] | None,
) -> None:
    reconciler._devtools_tracked_path = (
        reconciler._clone_inspected_value(path) if path is not None else None
    )


__all__ = [
    "clearDevtoolsErrorsAndWarnings",
    "clearDevtoolsErrorsForElement",
    "clearDevtoolsWarningsForElement",
    "copyDevtoolsElementPath",
    "deleteDevtoolsHookStatePath",
    "deleteDevtoolsPath",
    "deleteDevtoolsPropsPath",
    "deleteDevtoolsStatePath",
    "getDevtoolsBackendNotificationLog",
    "getDevtoolsLastCopiedValue",
    "getDevtoolsLastLoggedElement",
    "getDevtoolsMutableProps",
    "getDevtoolsStoredGlobals",
    "getDevtoolsTrackedPath",
    "logDevtoolsElementToConsole",
    "overrideDevtoolsError",
    "overrideDevtoolsHookState",
    "overrideDevtoolsProps",
    "overrideDevtoolsState",
    "overrideDevtoolsSuspense",
    "overrideDevtoolsSuspenseMilestone",
    "overrideDevtoolsValueAtPath",
    "recordDevtoolsBackendNotification",
    "renameDevtoolsHookStatePath",
    "renameDevtoolsPath",
    "renameDevtoolsPropsPath",
    "renameDevtoolsStatePath",
    "scheduleDevtoolsRetry",
    "scheduleDevtoolsUpdate",
    "setDevtoolsTrackedPath",
    "storeDevtoolsValueAsGlobal",
]
