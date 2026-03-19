"""Bridge request composition for the React DevTools backend facade."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from pyinkcli.packages.react_devtools_core.backend_constants import (
    CURRENT_BRIDGE_PROTOCOL,
)
from pyinkcli.packages.react_devtools_core.backend_handlers import (
    create_constant_response_handler as _create_constant_response_handler,
    create_delete_path_handler as _create_delete_path_handler,
    create_id_handler as _create_id_handler,
    create_legacy_override_handler as _create_legacy_override_handler,
    create_notification_handler as _create_notification_handler,
    create_override_value_handler as _create_override_value_handler,
    create_owners_list_handler as _create_owners_list_handler,
    create_rename_path_handler as _create_rename_path_handler,
    create_toggle_handler as _create_toggle_handler,
    normalize_id_payload as _normalize_id_payload,
)
from pyinkcli.packages.react_devtools_core.backend_inspection import (
    dispatchInspectScreenRequest as _dispatch_inspect_screen_request,
    package_version,
    syncSelectionState as _sync_selection_state,
)
from pyinkcli.packages.react_devtools_core.hydration import (
    dispatch_bridge_message,
    handle_inspect_element_bridge_call,
    make_bridge_success_response,
    make_devtools_backend_notification_handlers,
    normalize_inspect_element_bridge_payload,
)


def createBridgeDispatcher(
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


__all__ = ["createBridgeDispatcher"]
