"""Agent method composition for the React DevTools backend facade."""

from __future__ import annotations

from typing import Any

from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_agent_notification_method as _create_agent_notification_method,
    create_agent_request_method as _create_agent_request_method,
    create_element_path_lookup as _create_element_path_lookup,
    create_host_instance_id_lookup as _create_host_instance_id_lookup,
    create_host_instance_name_lookup as _create_host_instance_name_lookup,
    create_persisted_selection_clearer as _create_persisted_selection_clearer,
    create_persisted_selection_getter as _create_persisted_selection_getter,
    create_persisted_selection_match_getter as _create_persisted_selection_match_getter,
    create_persisted_selection_match_setter as _create_persisted_selection_match_setter,
    create_persisted_selection_setter as _create_persisted_selection_setter,
    create_stop_inspecting_native_handler as _create_stop_inspecting_native_handler,
    create_tracked_path_setter as _create_tracked_path_setter,
)
from pyinkcli.packages.react_devtools_core.backend_inspection import (
    normalizePersistedSelection as _normalize_persisted_selection,
    normalizePersistedSelectionMatch as _normalize_persisted_selection_match,
)


def createAgent(
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


__all__ = ["createAgent"]
