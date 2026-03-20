"""Source backend implementation mirroring react-devtools-core/src/backend.js."""

from __future__ import annotations

import socket
import warnings
from copy import deepcopy
from typing import Any

from pyinkcli.packages.react_devtools_core.backend_constants import (
    CURRENT_BRIDGE_PROTOCOL,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_agent_notification_method as _create_agent_notification_method,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_agent_request_method as _create_agent_request_method,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_constant_response_handler as _create_constant_response_handler,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_delete_path_handler as _create_delete_path_handler,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_element_path_lookup as _create_element_path_lookup,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_host_instance_id_lookup as _create_host_instance_id_lookup,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_host_instance_name_lookup as _create_host_instance_name_lookup,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_id_handler as _create_id_handler,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_legacy_override_handler as _create_legacy_override_handler,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_notification_handler as _create_notification_handler,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_override_value_handler as _create_override_value_handler,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_owners_list_handler as _create_owners_list_handler,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_persisted_selection_clearer as _create_persisted_selection_clearer,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_persisted_selection_getter as _create_persisted_selection_getter,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_persisted_selection_match_getter as _create_persisted_selection_match_getter,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_persisted_selection_match_setter as _create_persisted_selection_match_setter,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_persisted_selection_setter as _create_persisted_selection_setter,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_rename_path_handler as _create_rename_path_handler,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_stop_inspecting_native_handler as _create_stop_inspecting_native_handler,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_toggle_handler as _create_toggle_handler,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_tracked_path_setter as _create_tracked_path_setter,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    normalize_id_payload as _normalize_id_payload,
)
from pyinkcli.packages.react_devtools_core.backend_inspection import (
    dispatchInspectScreenRequest as _dispatch_inspect_screen_request,
)
from pyinkcli.packages.react_devtools_core.backend_inspection import (
    normalizePersistedSelection as _normalize_persisted_selection,
)
from pyinkcli.packages.react_devtools_core.backend_inspection import (
    normalizePersistedSelectionMatch as _normalize_persisted_selection_match,
)
from pyinkcli.packages.react_devtools_core.backend_inspection import (
    package_version,
)
from pyinkcli.packages.react_devtools_core.backend_inspection import (
    syncSelectionState as _sync_selection_state,
)
from pyinkcli.packages.react_devtools_core.hydration import (
    dispatch_bridge_message,
    handle_inspect_element_bridge_call,
    make_bridge_success_response,
    make_devtools_backend_notification_handlers,
    normalize_inspect_element_bridge_payload,
)
from pyinkcli.packages.react_devtools_core.window_polyfill import (
    installDevtoolsWindowPolyfill,
)

_devtools_initialized: bool = False


def _create_bridge_dispatcher(
    renderer_interface: dict[str, Any],
    *,
    state: dict[str, Any],
) -> dict[str, Any]:
    request_handlers = {
        "getOwnersList": _create_owners_list_handler(renderer_interface),
        "getBackendVersion": _create_constant_response_handler(
            renderer_interface,
            response_payload_factory=lambda: package_version(),
        ),
        "getBridgeProtocol": _create_constant_response_handler(
            renderer_interface,
            response_payload_factory=lambda: deepcopy(CURRENT_BRIDGE_PROTOCOL),
        ),
        "getProfilingStatus": _create_constant_response_handler(
            renderer_interface,
            response_payload_factory=lambda: False,
        ),
        "getProfilingData": _create_constant_response_handler(
            renderer_interface,
            response_payload_factory=renderer_interface["getProfilingData"],
        ),
        "overrideValueAtPath": _create_override_value_handler(renderer_interface),
        "overrideContext": _create_legacy_override_handler(
            renderer_interface,
            event="overrideContext",
            value_type="context",
        ),
        "overrideHookState": _create_legacy_override_handler(
            renderer_interface,
            event="overrideHookState",
            value_type="hooks",
            include_hook_id=True,
        ),
        "overrideProps": _create_legacy_override_handler(
            renderer_interface,
            event="overrideProps",
            value_type="props",
        ),
        "overrideState": _create_legacy_override_handler(
            renderer_interface,
            event="overrideState",
            value_type="state",
        ),
        "deletePath": _create_delete_path_handler(renderer_interface),
        "renamePath": _create_rename_path_handler(renderer_interface),
        "overrideError": _create_toggle_handler(
            renderer_interface,
            event="overrideError",
            method_name="overrideError",
            flag_key="forceError",
        ),
        "overrideSuspense": _create_toggle_handler(
            renderer_interface,
            event="overrideSuspense",
            method_name="overrideSuspense",
            flag_key="forceFallback",
        ),
        "scheduleUpdate": _create_id_handler(
            renderer_interface,
            event="scheduleUpdate",
            method_name="scheduleUpdate",
        ),
        "scheduleRetry": _create_id_handler(
            renderer_interface,
            event="scheduleRetry",
            method_name="scheduleRetry",
        ),
    }

    event_handlers = make_devtools_backend_notification_handlers(
        clear_errors_and_warnings=_create_notification_handler(
            renderer_interface,
            state=state,
            event="clearErrorsAndWarnings",
            method_name="clearErrorsAndWarnings",
        ),
        clear_errors_for_element=_create_notification_handler(
            renderer_interface,
            state=state,
            event="clearErrorsForElementID",
            method_name="clearErrorsForElementID",
        ),
        clear_warnings_for_element=_create_notification_handler(
            renderer_interface,
            state=state,
            event="clearWarningsForElementID",
            method_name="clearWarningsForElementID",
        ),
        copy_element_path=_create_notification_handler(
            renderer_interface,
            state=state,
            event="copyElementPath",
            method_name="copyElementPath",
        ),
        store_as_global=_create_notification_handler(
            renderer_interface,
            state=state,
            event="storeAsGlobal",
            method_name="storeAsGlobal",
        ),
        log_element_to_console=_create_notification_handler(
            renderer_interface,
            state=state,
            event="logElementToConsole",
            method_name="logElementToConsole",
        ),
        override_suspense_milestone=_create_notification_handler(
            renderer_interface,
            state=state,
            event="overrideSuspenseMilestone",
            method_name="overrideSuspenseMilestone",
        ),
    )

    def dispatchBridgeMessage(message: dict[str, Any]) -> Any:
        if not isinstance(message, dict):
            raise TypeError("Bridge message must be a dict")

        if message.get("type") == "request":
            event = message.get("event")
            request_id = message.get("requestId")
            if event == "inspectElement":
                normalized = normalize_inspect_element_bridge_payload(
                    message.get("payload", {}) or {},
                    request_id=request_id,
                )
                response = handle_inspect_element_bridge_call(
                    message,
                    renderer_interface["inspectElement"],
                )
                _sync_selection_state(
                    renderer_interface,
                    state,
                    node_id=normalized["id"],
                    renderer_id=normalized["rendererID"],
                )
                return response
            if event == "inspectScreen":
                return _dispatch_inspect_screen_request(message)
            if event == "getOwnersList":
                payload = message.get("payload", {}) or {}
                normalized = _normalize_id_payload(payload, event="getOwnersList")
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
            call_handlers=request_handlers,
            notification_handlers=event_handlers,
        )

    return {
        "requestHandlers": request_handlers,
        "eventHandlers": event_handlers,
        "dispatchBridgeMessage": dispatchBridgeMessage,
    }


def _create_agent(
    renderer_interface: dict[str, Any],
    *,
    state: dict[str, Any],
    dispatch_message: Any,
) -> dict[str, Any]:
    return {
        "getOwnersList": _create_agent_request_method(dispatch_message, "getOwnersList"),
        "getBackendVersion": _create_agent_request_method(dispatch_message, "getBackendVersion"),
        "getBridgeProtocol": _create_agent_request_method(dispatch_message, "getBridgeProtocol"),
        "getProfilingStatus": _create_agent_request_method(dispatch_message, "getProfilingStatus"),
        "getProfilingData": _create_agent_request_method(dispatch_message, "getProfilingData"),
        "inspectElement": _create_agent_request_method(dispatch_message, "inspectElement"),
        "inspectScreen": _create_agent_request_method(dispatch_message, "inspectScreen"),
        "overrideValueAtPath": _create_agent_request_method(dispatch_message, "overrideValueAtPath"),
        "overrideContext": _create_agent_request_method(dispatch_message, "overrideContext"),
        "overrideHookState": _create_agent_request_method(dispatch_message, "overrideHookState"),
        "overrideProps": _create_agent_request_method(dispatch_message, "overrideProps"),
        "overrideState": _create_agent_request_method(dispatch_message, "overrideState"),
        "deletePath": _create_agent_request_method(dispatch_message, "deletePath"),
        "renamePath": _create_agent_request_method(dispatch_message, "renamePath"),
        "overrideError": _create_agent_request_method(dispatch_message, "overrideError"),
        "overrideSuspense": _create_agent_request_method(dispatch_message, "overrideSuspense"),
        "scheduleUpdate": _create_agent_request_method(dispatch_message, "scheduleUpdate"),
        "scheduleRetry": _create_agent_request_method(dispatch_message, "scheduleRetry"),
        "clearErrorsAndWarnings": _create_agent_notification_method(dispatch_message, "clearErrorsAndWarnings"),
        "clearErrorsForElementID": _create_agent_notification_method(dispatch_message, "clearErrorsForElementID"),
        "clearWarningsForElementID": _create_agent_notification_method(dispatch_message, "clearWarningsForElementID"),
        "copyElementPath": _create_agent_notification_method(dispatch_message, "copyElementPath"),
        "storeAsGlobal": _create_agent_notification_method(dispatch_message, "storeAsGlobal"),
        "logElementToConsole": _create_agent_notification_method(dispatch_message, "logElementToConsole"),
        "overrideSuspenseMilestone": _create_agent_notification_method(
            dispatch_message,
            "overrideSuspenseMilestone",
        ),
        "getIDForHostInstance": _create_host_instance_id_lookup(),
        "getComponentNameForHostInstance": _create_host_instance_name_lookup(),
        "getPathForElement": _create_element_path_lookup(renderer_interface),
        "setTrackedPath": _create_tracked_path_setter(renderer_interface),
        "getPersistedSelection": _create_persisted_selection_getter(state),
        "setPersistedSelection": _create_persisted_selection_setter(
            renderer_interface,
            state,
            _normalize_persisted_selection,
        ),
        "clearPersistedSelection": _create_persisted_selection_clearer(renderer_interface, state),
        "getPersistedSelectionMatch": _create_persisted_selection_match_getter(state),
        "setPersistedSelectionMatch": _create_persisted_selection_match_setter(
            state,
            _normalize_persisted_selection_match,
        ),
        "stopInspectingNative": _create_stop_inspecting_native_handler(state),
    }


def createBackend(
    renderer_interface: dict[str, Any],
) -> dict[str, Any]:
    backend_state = {
        "lastNotification": None,
        "lastStopInspectingHostSelected": None,
        "lastSelectedElementID": None,
        "lastSelectedRendererID": None,
        "persistedSelection": None,
        "persistedSelectionMatch": None,
    }

    bridge_dispatcher = _create_bridge_dispatcher(
        renderer_interface,
        state=backend_state,
    )
    agent_methods = _create_agent(
        renderer_interface,
        state=backend_state,
        dispatch_message=bridge_dispatcher["dispatchBridgeMessage"],
    )

    return {
        "backendState": backend_state,
        **bridge_dispatcher,
        **agent_methods,
    }


def isBackendReachable(host: str = "localhost", port: int = 8097, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def initializeBackend() -> bool:
    global _devtools_initialized
    if _devtools_initialized:
        return True

    installDevtoolsWindowPolyfill()
    if isBackendReachable():
        _devtools_initialized = True
        return True

    warnings.warn(
        "DEV is set to true, but the React DevTools server is not running. "
        "Start it with:\n\n$ npx react-devtools\n",
        stacklevel=2,
    )
    return False


__all__ = [
    "CURRENT_BRIDGE_PROTOCOL",
    "createBackend",
    "initializeBackend",
    "installDevtoolsWindowPolyfill",
    "isBackendReachable",
]
