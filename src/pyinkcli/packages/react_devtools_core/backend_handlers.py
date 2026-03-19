"""Backend handler and agent factory helpers for React DevTools integration."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from pyinkcli.packages.react_devtools_core.hydration import (
    make_bridge_call,
    make_bridge_notification,
)
from pyinkcli.packages.react_devtools_core.window_polyfill import (
    installDevtoolsWindowPolyfill,
)


def create_notification_handler(
    renderer_interface: dict[str, Any],
    *,
    state: dict[str, Any],
    event: str,
    method_name: str,
) -> Callable[[dict[str, Any], dict[str, Any]], Any]:
    def handler(payload: dict[str, Any], _message: dict[str, Any]) -> Any:
        state["lastNotification"] = {
            "event": event,
            "payload": deepcopy(payload),
        }
        return renderer_interface[method_name](**normalize_keyword_arguments(payload))

    return handler


def create_owners_list_handler(
    renderer_interface: dict[str, Any],
) -> Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]:
    def handler(payload: dict[str, Any], _message: dict[str, Any]) -> dict[str, Any]:
        normalized = normalize_id_payload(payload, event="getOwnersList")
        return {
            "id": normalized["id"],
            "owners": renderer_interface["getOwnersList"](normalized["id"]),
        }

    return handler


def create_constant_response_handler(
    renderer_interface: dict[str, Any],
    *,
    response_payload_factory: Callable[[], Any],
) -> Callable[[dict[str, Any], dict[str, Any]], Any]:
    del renderer_interface

    def handler(_payload: dict[str, Any], _message: dict[str, Any]) -> Any:
        return response_payload_factory()

    return handler


def create_override_value_handler(
    renderer_interface: dict[str, Any],
) -> Callable[[dict[str, Any], dict[str, Any]], bool]:
    def handler(payload: dict[str, Any], _message: dict[str, Any]) -> bool:
        normalized = normalize_value_path_payload(
            payload,
            event="overrideValueAtPath",
            require_value=True,
        )
        return bool(
            renderer_interface["overrideValueAtPath"](
                normalized["valueType"],
                normalized["id"],
                normalized["hookID"],
                normalized["path"],
                normalized["value"],
            )
        )

    return handler


def create_delete_path_handler(
    renderer_interface: dict[str, Any],
) -> Callable[[dict[str, Any], dict[str, Any]], bool]:
    def handler(payload: dict[str, Any], _message: dict[str, Any]) -> bool:
        normalized = normalize_value_path_payload(
            payload,
            event="deletePath",
            require_value=False,
        )
        return bool(
            renderer_interface["deletePath"](
                normalized["valueType"],
                normalized["id"],
                normalized["hookID"],
                normalized["path"],
            )
        )

    return handler


def create_legacy_override_handler(
    renderer_interface: dict[str, Any],
    *,
    event: str,
    value_type: str,
    include_hook_id: bool = False,
) -> Callable[[dict[str, Any], dict[str, Any]], bool]:
    def handler(payload: dict[str, Any], _message: dict[str, Any]) -> bool:
        normalized = normalize_legacy_override_payload(
            payload,
            event=event,
            include_hook_id=include_hook_id,
        )
        if normalized["wasForwarded"]:
            return False
        return bool(
            renderer_interface["overrideValueAtPath"](
                value_type,
                normalized["id"],
                normalized["hookID"],
                normalized["path"],
                normalized["value"],
            )
        )

    return handler


def create_rename_path_handler(
    renderer_interface: dict[str, Any],
) -> Callable[[dict[str, Any], dict[str, Any]], bool]:
    def handler(payload: dict[str, Any], _message: dict[str, Any]) -> bool:
        normalized = normalize_rename_path_payload(payload)
        return bool(
            renderer_interface["renamePath"](
                normalized["valueType"],
                normalized["id"],
                normalized["hookID"],
                normalized["oldPath"],
                normalized["newPath"],
            )
        )

    return handler


def create_toggle_handler(
    renderer_interface: dict[str, Any],
    *,
    event: str,
    method_name: str,
    flag_key: str,
) -> Callable[[dict[str, Any], dict[str, Any]], bool]:
    def handler(payload: dict[str, Any], _message: dict[str, Any]) -> bool:
        normalized = normalize_id_flag_payload(payload, event=event, flag_key=flag_key)
        return bool(renderer_interface[method_name](normalized["id"], normalized[flag_key]))

    return handler


def create_id_handler(
    renderer_interface: dict[str, Any],
    *,
    event: str,
    method_name: str,
) -> Callable[[dict[str, Any], dict[str, Any]], bool]:
    def handler(payload: dict[str, Any], _message: dict[str, Any]) -> bool:
        normalized = normalize_id_payload(payload, event=event)
        return bool(renderer_interface[method_name](normalized["id"]))

    return handler


def normalize_value_path_payload(
    payload: dict[str, Any] | None,
    *,
    event: str,
    require_value: bool,
) -> dict[str, Any]:
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise TypeError(f"{event} payload must be a dict")
    node_id = payload.get("id")
    value_type = payload.get("valueType", payload.get("type"))
    path = payload.get("path")
    hook_id = payload.get("hookID", payload.get("hookId"))
    if not isinstance(node_id, str) or not node_id:
        raise ValueError(f"{event} payload must include a non-empty 'id'")
    if not isinstance(value_type, str) or not value_type:
        raise ValueError(f"{event} payload must include a non-empty 'valueType'")
    if not isinstance(path, list):
        raise TypeError(f"{event} payload 'path' must be a list")
    normalized = {
        "id": node_id,
        "valueType": value_type,
        "hookID": hook_id,
        "path": list(path),
    }
    if require_value:
        if "value" not in payload:
            raise ValueError(f"{event} payload must include 'value'")
        normalized["value"] = payload["value"]
    return normalized


def normalize_rename_path_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise TypeError("renamePath payload must be a dict")
    base = normalize_value_path_payload(payload, event="renamePath", require_value=False)
    new_path = payload.get("newPath")
    if not isinstance(new_path, list):
        raise TypeError("renamePath payload 'newPath' must be a list")
    return {
        **base,
        "oldPath": base["path"],
        "newPath": list(new_path),
    }


def normalize_legacy_override_payload(
    payload: dict[str, Any] | None,
    *,
    event: str,
    include_hook_id: bool,
) -> dict[str, Any]:
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise TypeError(f"{event} payload must be a dict")
    node_id = payload.get("id")
    path = payload.get("path")
    was_forwarded = payload.get("wasForwarded", False)
    hook_id = payload.get("hookID", payload.get("hookId"))
    if not isinstance(node_id, str) or not node_id:
        raise ValueError(f"{event} payload must include a non-empty 'id'")
    if not isinstance(path, list):
        raise TypeError(f"{event} payload 'path' must be a list")
    if not isinstance(was_forwarded, bool):
        raise TypeError(f"{event} payload 'wasForwarded' must be a bool")
    if "value" not in payload:
        raise ValueError(f"{event} payload must include 'value'")
    return {
        "id": node_id,
        "path": list(path),
        "value": payload["value"],
        "hookID": hook_id if include_hook_id else None,
        "wasForwarded": was_forwarded,
    }


def normalize_id_flag_payload(
    payload: dict[str, Any] | None,
    *,
    event: str,
    flag_key: str,
) -> dict[str, Any]:
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise TypeError(f"{event} payload must be a dict")
    node_id = payload.get("id")
    flag_value = payload.get(flag_key)
    if not isinstance(node_id, str) or not node_id:
        raise ValueError(f"{event} payload must include a non-empty 'id'")
    if not isinstance(flag_value, bool):
        raise TypeError(f"{event} payload '{flag_key}' must be a bool")
    return {"id": node_id, flag_key: flag_value}


def normalize_id_payload(
    payload: dict[str, Any] | None,
    *,
    event: str,
) -> dict[str, Any]:
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise TypeError(f"{event} payload must be a dict")
    node_id = payload.get("id")
    if not isinstance(node_id, str) or not node_id:
        raise ValueError(f"{event} payload must include a non-empty 'id'")
    return {"id": node_id}


def normalize_keyword_arguments(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    if "rendererID" in normalized:
        normalized["renderer_id"] = normalized.pop("rendererID")
    if "suspendedSet" in normalized:
        normalized["suspended_set"] = normalized.pop("suspendedSet")
    return normalized


def create_agent_request_method(
    dispatch_message: Callable[[dict[str, Any]], Any],
    event: str,
) -> Callable[[dict[str, Any] | None], Any]:
    def method(params: dict[str, Any] | None = None) -> Any:
        payload = {} if params is None else dict(params)
        request_id = payload.pop("requestID", payload.pop("requestId", None))
        message = make_bridge_call(event, payload, request_id=request_id)
        return dispatch_message(message)

    return method


def create_agent_notification_method(
    dispatch_message: Callable[[dict[str, Any]], Any],
    event: str,
) -> Callable[[dict[str, Any] | None], Any]:
    def method(params: dict[str, Any] | None = None) -> Any:
        payload = {} if params is None else dict(params)
        message = make_bridge_notification(event, payload)
        dispatch_message(message)
        return None

    return method


def create_host_instance_id_lookup() -> Callable[[Any, bool], dict[str, Any] | None]:
    def method(target: Any, only_suspense_nodes: bool = False) -> dict[str, Any] | None:
        global_scope = installDevtoolsWindowPolyfill()
        renderers = global_scope.get("__INK_DEVTOOLS_RENDERERS__", {})
        for renderer_id, renderer in renderers.items():
            if not isinstance(renderer, dict):
                continue
            lookup_name = (
                "getSuspenseNodeIDForHostInstance"
                if only_suspense_nodes
                else "getElementIDForHostInstance"
            )
            lookup = renderer.get(lookup_name)
            if not callable(lookup):
                continue
            try:
                node_id = lookup(target)
            except Exception:
                continue
            if node_id is not None:
                return {
                    "id": node_id,
                    "rendererID": int(renderer_id),
                }
        return None

    return method


def create_host_instance_name_lookup() -> Callable[[Any], str | None]:
    get_id_for_host_instance = create_host_instance_id_lookup()

    def method(target: Any) -> str | None:
        match = get_id_for_host_instance(target)
        if match is None:
            return None
        global_scope = installDevtoolsWindowPolyfill()
        renderer = global_scope.get("__INK_DEVTOOLS_RENDERERS__", {}).get(match["rendererID"])
        if not isinstance(renderer, dict):
            return None
        get_display_name = renderer.get("getDisplayNameForNode")
        if not callable(get_display_name):
            return None
        return get_display_name(match["id"])

    return method


def create_element_path_lookup(
    renderer_interface: dict[str, Any],
) -> Callable[[Any], list[dict[str, Any]] | None]:
    def method(node_id: Any) -> list[dict[str, Any]] | None:
        return renderer_interface["getPathForElement"](node_id)

    return method


def create_tracked_path_setter(
    renderer_interface: dict[str, Any],
) -> Callable[[list[dict[str, Any]] | None], None]:
    def method(path: list[dict[str, Any]] | None) -> None:
        renderer_interface["setTrackedPath"](deepcopy(path) if path is not None else None)

    return method


def create_persisted_selection_getter(
    state: dict[str, Any],
) -> Callable[[], dict[str, Any] | None]:
    def method() -> dict[str, Any] | None:
        selection = state.get("persistedSelection")
        return deepcopy(selection) if selection is not None else None

    return method


def create_persisted_selection_setter(
    renderer_interface: dict[str, Any],
    state: dict[str, Any],
    normalize_persisted_selection: Callable[[dict[str, Any] | None], dict[str, Any] | None],
) -> Callable[[dict[str, Any] | None], None]:
    current_renderer_id = renderer_interface.get("rendererID")

    def method(selection: dict[str, Any] | None) -> None:
        normalized = normalize_persisted_selection(selection)
        state["persistedSelection"] = deepcopy(normalized) if normalized is not None else None
        state["persistedSelectionMatch"] = None
        if normalized is None:
            renderer_interface["setTrackedPath"](None)
            return
        if normalized["rendererID"] == current_renderer_id:
            renderer_interface["setTrackedPath"](deepcopy(normalized["path"]))

    return method


def create_persisted_selection_clearer(
    renderer_interface: dict[str, Any],
    state: dict[str, Any],
) -> Callable[[], None]:
    def method() -> None:
        state["persistedSelection"] = None
        state["persistedSelectionMatch"] = None
        renderer_interface["setTrackedPath"](None)

    return method


def create_persisted_selection_match_getter(
    state: dict[str, Any],
) -> Callable[[], dict[str, Any] | None]:
    def method() -> dict[str, Any] | None:
        match = state.get("persistedSelectionMatch")
        return deepcopy(match) if match is not None else None

    return method


def create_persisted_selection_match_setter(
    state: dict[str, Any],
    normalize_persisted_selection_match: Callable[[dict[str, Any] | None], dict[str, Any] | None],
) -> Callable[[dict[str, Any] | None], None]:
    def method(match: dict[str, Any] | None) -> None:
        normalized = normalize_persisted_selection_match(match)
        state["persistedSelectionMatch"] = deepcopy(normalized) if normalized is not None else None

    return method


def create_stop_inspecting_native_handler(
    state: dict[str, Any],
) -> Callable[[bool], None]:
    def method(selected: bool = False) -> None:
        if not isinstance(selected, bool):
            raise TypeError("stopInspectingNative selected flag must be a bool")
        state["lastStopInspectingHostSelected"] = selected
        installDevtoolsWindowPolyfill()["__INK_DEVTOOLS_STOP_INSPECTING_HOST__"] = selected

    return method


__all__ = [
    "create_agent_notification_method",
    "create_agent_request_method",
    "create_constant_response_handler",
    "create_delete_path_handler",
    "create_element_path_lookup",
    "create_host_instance_id_lookup",
    "create_host_instance_name_lookup",
    "create_id_handler",
    "create_legacy_override_handler",
    "create_notification_handler",
    "create_override_value_handler",
    "create_owners_list_handler",
    "create_persisted_selection_clearer",
    "create_persisted_selection_getter",
    "create_persisted_selection_match_getter",
    "create_persisted_selection_match_setter",
    "create_persisted_selection_setter",
    "create_rename_path_handler",
    "create_stop_inspecting_native_handler",
    "create_toggle_handler",
    "create_tracked_path_setter",
    "normalize_id_flag_payload",
    "normalize_id_payload",
    "normalize_keyword_arguments",
    "normalize_legacy_override_payload",
    "normalize_rename_path_payload",
    "normalize_value_path_payload",
]
