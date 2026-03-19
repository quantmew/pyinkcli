"""Devtools integration matching JS `devtools.ts`."""

from __future__ import annotations

import socket
import warnings
from copy import deepcopy
from typing import Any, Callable

from ink_python.devtools_hydration import (
    dispatch_bridge_message,
    handle_inspect_element_bridge_call,
    make_bridge_call,
    make_bridge_notification,
    make_bridge_success_response,
    normalize_inspect_screen_bridge_payload,
    make_devtools_backend_notification_handlers,
)
from ink_python.devtools_window_polyfill import installDevtoolsWindowPolyfill


_devtools_initialized: bool = False
CURRENT_BRIDGE_PROTOCOL = {
    "version": 2,
    "minNpmVersion": "4.22.0",
    "maxNpmVersion": None,
}


def isDevToolsReachable(host: str = "localhost", port: int = 8097, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def initializeDevtools() -> bool:
    global _devtools_initialized
    if _devtools_initialized:
        return True

    installDevtoolsWindowPolyfill()
    if isDevToolsReachable():
        _devtools_initialized = True
        return True

    warnings.warn(
        "DEV is set to true, but the React DevTools server is not running. "
        "Start it with:\n\n$ npx react-devtools\n",
        stacklevel=2,
    )
    return False


def createDevtoolsBackendFacade(
    renderer_interface: dict[str, Any],
) -> dict[str, Any]:
    state = {
        "lastNotification": None,
        "lastStopInspectingHostSelected": None,
    }

    call_handlers = {
        "getOwnersList": _make_get_owners_list_handler(renderer_interface),
        "getBackendVersion": _make_constant_response_handler(
            renderer_interface,
            response_payload_factory=lambda: package_version(),
        ),
        "getBridgeProtocol": _make_constant_response_handler(
            renderer_interface,
            response_payload_factory=lambda: deepcopy(CURRENT_BRIDGE_PROTOCOL),
        ),
        "getProfilingStatus": _make_constant_response_handler(
            renderer_interface,
            response_payload_factory=lambda: False,
        ),
        "getProfilingData": _make_constant_response_handler(
            renderer_interface,
            response_payload_factory=renderer_interface["getProfilingData"],
        ),
        "overrideValueAtPath": _make_override_value_at_path_handler(renderer_interface),
        "overrideContext": _make_legacy_override_value_handler(
            renderer_interface,
            event="overrideContext",
            value_type="context",
        ),
        "overrideHookState": _make_legacy_override_value_handler(
            renderer_interface,
            event="overrideHookState",
            value_type="hooks",
            include_hook_id=True,
        ),
        "overrideProps": _make_legacy_override_value_handler(
            renderer_interface,
            event="overrideProps",
            value_type="props",
        ),
        "overrideState": _make_legacy_override_value_handler(
            renderer_interface,
            event="overrideState",
            value_type="state",
        ),
        "deletePath": _make_delete_path_handler(renderer_interface),
        "renamePath": _make_rename_path_handler(renderer_interface),
        "overrideError": _make_toggle_handler(
            renderer_interface,
            event="overrideError",
            method_name="overrideError",
            flag_key="forceError",
        ),
        "overrideSuspense": _make_toggle_handler(
            renderer_interface,
            event="overrideSuspense",
            method_name="overrideSuspense",
            flag_key="forceFallback",
        ),
        "scheduleUpdate": _make_id_only_handler(
            renderer_interface,
            event="scheduleUpdate",
            method_name="scheduleUpdate",
        ),
        "scheduleRetry": _make_id_only_handler(
            renderer_interface,
            event="scheduleRetry",
            method_name="scheduleRetry",
        ),
    }

    notification_handlers = make_devtools_backend_notification_handlers(
        clear_errors_and_warnings=_make_notification_handler(
            renderer_interface,
            state=state,
            event="clearErrorsAndWarnings",
            method_name="clearErrorsAndWarnings",
        ),
        clear_errors_for_element=_make_notification_handler(
            renderer_interface,
            state=state,
            event="clearErrorsForElementID",
            method_name="clearErrorsForElementID",
        ),
        clear_warnings_for_element=_make_notification_handler(
            renderer_interface,
            state=state,
            event="clearWarningsForElementID",
            method_name="clearWarningsForElementID",
        ),
        copy_element_path=_make_notification_handler(
            renderer_interface,
            state=state,
            event="copyElementPath",
            method_name="copyElementPath",
        ),
        store_as_global=_make_notification_handler(
            renderer_interface,
            state=state,
            event="storeAsGlobal",
            method_name="storeAsGlobal",
        ),
        log_element_to_console=_make_notification_handler(
            renderer_interface,
            state=state,
            event="logElementToConsole",
            method_name="logElementToConsole",
        ),
        override_suspense_milestone=_make_notification_handler(
            renderer_interface,
            state=state,
            event="overrideSuspenseMilestone",
            method_name="overrideSuspenseMilestone",
        ),
    )

    def dispatch_message(message: dict[str, Any]) -> Any:
        if not isinstance(message, dict):
            raise TypeError("Bridge message must be a dict")

        if message.get("type") == "request":
            event = message.get("event")
            request_id = message.get("requestId")
            if event == "inspectElement":
                return handle_inspect_element_bridge_call(
                    message,
                    renderer_interface["inspectElement"],
                )
            if event == "inspectScreen":
                return _handle_inspect_screen_bridge_call_across_renderers(message)
            if event == "getOwnersList":
                payload = message.get("payload", {}) or {}
                normalized = _normalize_id_only_payload(payload, event="getOwnersList")
                return make_bridge_success_response(
                    "ownersList",
                    {
                        "id": normalized["id"],
                        "owners": renderer_interface["getOwnersList"](normalized["id"]),
                    },
                    request_id=request_id,
                )
            if event == "getBackendVersion":
                return make_bridge_success_response(
                    "backendVersion",
                    {"version": package_version()},
                    request_id=request_id,
                )
            if event == "getBridgeProtocol":
                return make_bridge_success_response(
                    "bridgeProtocol",
                    {"bridgeProtocol": deepcopy(CURRENT_BRIDGE_PROTOCOL)},
                    request_id=request_id,
                )
            if event == "getProfilingStatus":
                return make_bridge_success_response(
                    "profilingStatus",
                    {"isProfiling": False},
                    request_id=request_id,
                )
            if event == "getProfilingData":
                return make_bridge_success_response(
                    "profilingData",
                    renderer_interface["getProfilingData"](),
                    request_id=request_id,
                )

        return dispatch_bridge_message(
            message,
            call_handlers=call_handlers,
            notification_handlers=notification_handlers,
        )

    agent_methods = {
        "getOwnersList": _make_agent_request_method(dispatch_message, "getOwnersList"),
        "getBackendVersion": _make_agent_request_method(dispatch_message, "getBackendVersion"),
        "getBridgeProtocol": _make_agent_request_method(dispatch_message, "getBridgeProtocol"),
        "getProfilingStatus": _make_agent_request_method(dispatch_message, "getProfilingStatus"),
        "getProfilingData": _make_agent_request_method(dispatch_message, "getProfilingData"),
        "inspectElement": _make_agent_request_method(dispatch_message, "inspectElement"),
        "inspectScreen": _make_agent_request_method(dispatch_message, "inspectScreen"),
        "overrideValueAtPath": _make_agent_request_method(dispatch_message, "overrideValueAtPath"),
        "overrideContext": _make_agent_request_method(dispatch_message, "overrideContext"),
        "overrideHookState": _make_agent_request_method(dispatch_message, "overrideHookState"),
        "overrideProps": _make_agent_request_method(dispatch_message, "overrideProps"),
        "overrideState": _make_agent_request_method(dispatch_message, "overrideState"),
        "deletePath": _make_agent_request_method(dispatch_message, "deletePath"),
        "renamePath": _make_agent_request_method(dispatch_message, "renamePath"),
        "overrideError": _make_agent_request_method(dispatch_message, "overrideError"),
        "overrideSuspense": _make_agent_request_method(dispatch_message, "overrideSuspense"),
        "scheduleUpdate": _make_agent_request_method(dispatch_message, "scheduleUpdate"),
        "scheduleRetry": _make_agent_request_method(dispatch_message, "scheduleRetry"),
        "clearErrorsAndWarnings": _make_agent_notification_method(dispatch_message, "clearErrorsAndWarnings"),
        "clearErrorsForElementID": _make_agent_notification_method(dispatch_message, "clearErrorsForElementID"),
        "clearWarningsForElementID": _make_agent_notification_method(dispatch_message, "clearWarningsForElementID"),
        "copyElementPath": _make_agent_notification_method(dispatch_message, "copyElementPath"),
        "storeAsGlobal": _make_agent_notification_method(dispatch_message, "storeAsGlobal"),
        "logElementToConsole": _make_agent_notification_method(dispatch_message, "logElementToConsole"),
        "overrideSuspenseMilestone": _make_agent_notification_method(
            dispatch_message,
            "overrideSuspenseMilestone",
        ),
        "getIDForHostInstance": _make_get_id_for_host_instance_method(),
        "getComponentNameForHostInstance": _make_get_component_name_for_host_instance_method(),
        "getPathForElement": _make_get_path_for_element_method(renderer_interface),
        "setTrackedPath": _make_set_tracked_path_method(renderer_interface),
        "stopInspectingNative": _make_stop_inspecting_native_method(state),
    }

    return {
        "callHandlers": call_handlers,
        "notificationHandlers": notification_handlers,
        "dispatchMessage": dispatch_message,
        "state": state,
        **agent_methods,
    }


def _make_notification_handler(
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
        return renderer_interface[method_name](**_normalize_keyword_arguments(payload))

    return handler


def _make_get_owners_list_handler(
    renderer_interface: dict[str, Any],
) -> Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]:
    def handler(payload: dict[str, Any], _message: dict[str, Any]) -> dict[str, Any]:
        normalized = _normalize_id_only_payload(payload, event="getOwnersList")
        return {
            "id": normalized["id"],
            "owners": renderer_interface["getOwnersList"](normalized["id"]),
        }

    return handler


def _make_constant_response_handler(
    renderer_interface: dict[str, Any],
    *,
    response_payload_factory: Callable[[], Any],
) -> Callable[[dict[str, Any], dict[str, Any]], Any]:
    del renderer_interface

    def handler(_payload: dict[str, Any], _message: dict[str, Any]) -> Any:
        return response_payload_factory()

    return handler


def _make_override_value_at_path_handler(
    renderer_interface: dict[str, Any],
) -> Callable[[dict[str, Any], dict[str, Any]], bool]:
    def handler(payload: dict[str, Any], _message: dict[str, Any]) -> bool:
        normalized = _normalize_value_path_payload(
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


def _make_delete_path_handler(
    renderer_interface: dict[str, Any],
) -> Callable[[dict[str, Any], dict[str, Any]], bool]:
    def handler(payload: dict[str, Any], _message: dict[str, Any]) -> bool:
        normalized = _normalize_value_path_payload(
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


def _make_legacy_override_value_handler(
    renderer_interface: dict[str, Any],
    *,
    event: str,
    value_type: str,
    include_hook_id: bool = False,
) -> Callable[[dict[str, Any], dict[str, Any]], bool]:
    def handler(payload: dict[str, Any], _message: dict[str, Any]) -> bool:
        normalized = _normalize_legacy_override_payload(
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


def _make_rename_path_handler(
    renderer_interface: dict[str, Any],
) -> Callable[[dict[str, Any], dict[str, Any]], bool]:
    def handler(payload: dict[str, Any], _message: dict[str, Any]) -> bool:
        normalized = _normalize_rename_path_payload(payload)
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


def _make_toggle_handler(
    renderer_interface: dict[str, Any],
    *,
    event: str,
    method_name: str,
    flag_key: str,
) -> Callable[[dict[str, Any], dict[str, Any]], bool]:
    def handler(payload: dict[str, Any], _message: dict[str, Any]) -> bool:
        normalized = _normalize_id_flag_payload(payload, event=event, flag_key=flag_key)
        return bool(renderer_interface[method_name](normalized["id"], normalized[flag_key]))

    return handler


def _make_id_only_handler(
    renderer_interface: dict[str, Any],
    *,
    event: str,
    method_name: str,
) -> Callable[[dict[str, Any], dict[str, Any]], bool]:
    def handler(payload: dict[str, Any], _message: dict[str, Any]) -> bool:
        normalized = _normalize_id_only_payload(payload, event=event)
        return bool(renderer_interface[method_name](normalized["id"]))

    return handler


def _normalize_value_path_payload(
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


def _normalize_rename_path_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise TypeError("renamePath payload must be a dict")
    base = _normalize_value_path_payload(payload, event="renamePath", require_value=False)
    new_path = payload.get("newPath")
    if not isinstance(new_path, list):
        raise TypeError("renamePath payload 'newPath' must be a list")
    return {
        **base,
        "oldPath": base["path"],
        "newPath": list(new_path),
    }


def _normalize_legacy_override_payload(
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


def _normalize_id_flag_payload(
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


def _normalize_id_only_payload(
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


def _normalize_keyword_arguments(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    if "rendererID" in normalized:
        normalized["renderer_id"] = normalized.pop("rendererID")
    if "suspendedSet" in normalized:
        normalized["suspended_set"] = normalized.pop("suspendedSet")
    return normalized


def _make_agent_request_method(
    dispatch_message: Callable[[dict[str, Any]], Any],
    event: str,
) -> Callable[[dict[str, Any] | None], Any]:
    def method(params: dict[str, Any] | None = None) -> Any:
        payload = {} if params is None else dict(params)
        request_id = payload.pop("requestID", payload.pop("requestId", None))
        message = make_bridge_call(event, payload, request_id=request_id)
        return dispatch_message(message)

    return method


def _make_agent_notification_method(
    dispatch_message: Callable[[dict[str, Any]], Any],
    event: str,
) -> Callable[[dict[str, Any] | None], Any]:
    def method(params: dict[str, Any] | None = None) -> Any:
        payload = {} if params is None else dict(params)
        message = make_bridge_notification(event, payload)
        dispatch_message(message)
        return None

    return method


def _make_get_id_for_host_instance_method() -> Callable[[Any, bool], dict[str, Any] | None]:
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


def _make_get_component_name_for_host_instance_method() -> Callable[[Any], str | None]:
    get_id_for_host_instance = _make_get_id_for_host_instance_method()

    def method(target: Any) -> str | None:
        match = get_id_for_host_instance(target)
        if match is None:
            return None
        global_scope = installDevtoolsWindowPolyfill()
        renderer = global_scope.get("__INK_DEVTOOLS_RENDERERS__", {}).get(match["rendererID"])
        if not isinstance(renderer, dict):
            return None
        get_display_name = renderer.get("getDisplayNameForElementID", renderer.get("getDisplayNameForNode"))
        if not callable(get_display_name):
            return None
        return get_display_name(match["id"])

    return method


def _make_get_path_for_element_method(
    renderer_interface: dict[str, Any],
) -> Callable[[Any], list[dict[str, Any]] | None]:
    def method(node_id: Any) -> list[dict[str, Any]] | None:
        return renderer_interface["getPathForElement"](node_id)

    return method


def _make_set_tracked_path_method(
    renderer_interface: dict[str, Any],
) -> Callable[[list[dict[str, Any]] | None], None]:
    def method(path: list[dict[str, Any]] | None) -> None:
        renderer_interface["setTrackedPath"](deepcopy(path) if path is not None else None)

    return method


def _make_stop_inspecting_native_method(
    state: dict[str, Any],
) -> Callable[[bool], None]:
    def method(selected: bool = False) -> None:
        if not isinstance(selected, bool):
            raise TypeError("stopInspectingNative selected flag must be a bool")
        state["lastStopInspectingHostSelected"] = selected
        installDevtoolsWindowPolyfill()["__INK_DEVTOOLS_STOP_INSPECTING_HOST__"] = selected

    return method


def _handle_inspect_screen_bridge_call_across_renderers(
    message: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(message, dict):
        raise TypeError("Bridge call message must be a dict")
    if message.get("type") != "request":
        raise ValueError("Bridge call message must have type='request'")
    if message.get("event") != "inspectScreen":
        raise ValueError("Bridge call message event must be 'inspectScreen'")
    if "requestId" not in message:
        raise ValueError("Bridge call message must include requestId")

    payload = message.get("payload", {})
    if payload is None:
        payload = {}
    normalized = normalize_inspect_screen_bridge_payload(
        payload,
        request_id=message["requestId"],
    )
    result = _inspect_screen_across_renderers(
        request_id=normalized["requestID"],
        node_id=normalized["id"],
        path=normalized["path"],
        force_full_data=normalized["forceFullData"],
    )
    return make_bridge_success_response(
        "inspectedScreen",
        result,
        request_id=message["requestId"],
    )


def package_version() -> str:
    from ink_python.reconciler import packageInfo

    return str(packageInfo["version"])


def _inspect_screen_across_renderers(
    *,
    request_id: Any,
    node_id: Any,
    path: list[Any] | None,
    force_full_data: bool,
) -> dict[str, Any]:
    global_scope = installDevtoolsWindowPolyfill()
    renderers = global_scope.get("__INK_DEVTOOLS_RENDERERS__", {})
    inspected_screen: dict[str, Any] | None = None
    found = False
    suspended_by_offset = 0
    suspended_by_path_index: int | None = None
    renderer_path: list[Any] | None = None

    if path is not None and len(path) > 1:
        if path[0] != "suspendedBy":
            raise ValueError("Only hydrating suspendedBy paths is supported")
        if not isinstance(path[1], int):
            raise TypeError("inspectScreen suspendedBy index must be a number")
        suspended_by_path_index = path[1]
        renderer_path = list(path[2:])

    for renderer in renderers.values():
        if not isinstance(renderer, dict) or "inspectElement" not in renderer:
            continue

        renderer_path_for_call: list[Any] | None = None
        if suspended_by_path_index is not None:
            renderer_index = suspended_by_path_index - suspended_by_offset
            attribute = renderer["getElementAttributeByPath"](
                node_id,
                ["suspendedBy", renderer_index],
            )
            if attribute is not None:
                renderer_path_for_call = ["suspendedBy", renderer_index, *(renderer_path or [])]

        inspected_roots_payload = renderer["inspectElement"](
            request_id,
            node_id,
            renderer_path_for_call,
            force_full_data,
        )
        payload_type = inspected_roots_payload.get("type")
        if payload_type == "hydrated-path":
            adjusted = deepcopy(inspected_roots_payload)
            adjusted_path = adjusted.get("path")
            if isinstance(adjusted_path, list) and len(adjusted_path) > 1:
                adjusted_path[1] += suspended_by_offset
            adjusted_value = adjusted.get("value")
            if (
                isinstance(adjusted_value, dict)
                and isinstance(adjusted_value.get("cleaned"), list)
            ):
                for cleaned_path in adjusted_value["cleaned"]:
                    if (
                        isinstance(cleaned_path, list)
                        and len(cleaned_path) > 1
                        and isinstance(cleaned_path[1], int)
                    ):
                        cleaned_path[1] += suspended_by_offset
            return adjusted
        if payload_type == "full-data":
            inspected_roots = inspected_roots_payload.get("value")
            if isinstance(inspected_roots, dict):
                if inspected_screen is None:
                    inspected_screen = _create_empty_inspected_screen(
                        inspected_roots.get("id", node_id),
                        inspected_roots.get("type", "root"),
                    )
                _merge_inspected_roots(
                    inspected_screen,
                    inspected_roots,
                    suspended_by_offset=suspended_by_offset,
                )
                suspended_by = inspected_roots.get("suspendedBy", {})
                suspended_by_data = suspended_by.get("data", []) if isinstance(suspended_by, dict) else []
                suspended_by_offset += len(suspended_by_data) if isinstance(suspended_by_data, list) else 0
                found = True
            continue
        if payload_type == "no-change":
            roots_suspended_by = renderer["getElementAttributeByPath"](node_id, ["suspendedBy"])
            if isinstance(roots_suspended_by, list):
                suspended_by_offset += len(roots_suspended_by)
            found = True
            continue
        if payload_type == "error":
            return deepcopy(inspected_roots_payload)

    if inspected_screen is None:
        if found:
            return {
                "type": "no-change",
                "responseID": request_id,
                "id": node_id,
            }
        return {
            "type": "not-found",
            "responseID": request_id,
            "id": node_id,
        }

    return {
        "type": "full-data",
        "responseID": request_id,
        "id": node_id,
        "value": inspected_screen,
    }


def _create_empty_inspected_screen(
    arbitrary_root_id: Any,
    element_type: Any,
) -> dict[str, Any]:
    return {
        "id": arbitrary_root_id,
        "type": element_type,
        "isErrored": False,
        "errors": [],
        "warnings": [],
        "suspendedBy": {
            "data": [],
            "cleaned": [],
            "unserializable": [],
        },
        "suspendedByRange": None,
        "unknownSuspenders": 0,
        "rootType": None,
        "plugins": {"stylex": None},
        "nativeTag": None,
        "env": None,
        "source": None,
        "stack": None,
        "rendererPackageName": None,
        "rendererVersion": None,
        "key": None,
        "canEditFunctionProps": False,
        "canEditHooks": False,
        "canEditFunctionPropsDeletePaths": False,
        "canEditFunctionPropsRenamePaths": False,
        "canEditHooksAndDeletePaths": False,
        "canEditHooksAndRenamePaths": False,
        "canToggleError": False,
        "canToggleSuspense": False,
        "isSuspended": False,
        "hasLegacyContext": False,
        "context": None,
        "hooks": None,
        "props": None,
        "state": None,
        "owners": None,
    }


def _merge_inspected_roots(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    suspended_by_offset: int,
) -> None:
    if right.get("isErrored"):
        left["isErrored"] = True
    left.setdefault("errors", []).extend(deepcopy(right.get("errors", [])))
    left.setdefault("warnings", []).extend(deepcopy(right.get("warnings", [])))

    left_suspended_by = left.setdefault(
        "suspendedBy",
        {"data": [], "cleaned": [], "unserializable": []},
    )
    right_suspended_by = right.get("suspendedBy") or {}
    right_data = right_suspended_by.get("data", []) if isinstance(right_suspended_by, dict) else []
    right_cleaned = right_suspended_by.get("cleaned", []) if isinstance(right_suspended_by, dict) else []
    right_unserializable = (
        right_suspended_by.get("unserializable", []) if isinstance(right_suspended_by, dict) else []
    )
    left_suspended_by["data"].extend(deepcopy(right_data))
    for cleaned_path in right_cleaned:
        left_suspended_by["cleaned"].append(
            [suspended_by_offset + cleaned_path[0], *deepcopy(cleaned_path[1:])]
        )
    for unserializable_path in right_unserializable:
        left_suspended_by["unserializable"].append(
            [suspended_by_offset + unserializable_path[0], *deepcopy(unserializable_path[1:])]
        )

    left_range = left.get("suspendedByRange")
    right_range = right.get("suspendedByRange")
    if isinstance(right_range, list) and len(right_range) == 2:
        if left_range is None:
            left["suspendedByRange"] = [right_range[0], right_range[1]]
        else:
            left_range[0] = min(left_range[0], right_range[0])
            left_range[1] = max(left_range[1], right_range[1])
