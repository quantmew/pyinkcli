"""Selection and inspect-screen helpers for React DevTools backend."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from pyinkcli.packages.react_devtools_core.hydration import (
    make_bridge_success_response,
    normalize_inspect_screen_bridge_payload,
)
from pyinkcli.packages.react_devtools_core.window_polyfill import (
    installDevtoolsWindowPolyfill,
)


def normalizePersistedSelection(
    selection: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if selection is None:
        return None
    if not isinstance(selection, dict):
        raise TypeError("Persisted selection must be a dict or None")

    renderer_id = selection.get("rendererID", selection.get("rendererId"))
    path = selection.get("path")
    if not isinstance(renderer_id, int):
        raise TypeError("Persisted selection 'rendererID' must be an int")
    if not isinstance(path, list):
        raise TypeError("Persisted selection 'path' must be a list")

    return {
        "rendererID": renderer_id,
        "path": deepcopy(path),
    }


def normalizePersistedSelectionMatch(
    match: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if match is None:
        return None
    if not isinstance(match, dict):
        raise TypeError("Persisted selection match must be a dict or None")
    node_id = match.get("id")
    if not isinstance(node_id, str) or not node_id:
        raise ValueError("Persisted selection match must include a non-empty 'id'")
    if "isFullMatch" in match and not isinstance(match["isFullMatch"], bool):
        raise TypeError("Persisted selection match 'isFullMatch' must be a bool")
    if "rendererID" in match and not isinstance(match["rendererID"], int):
        raise TypeError("Persisted selection match 'rendererID' must be an int")
    if "path" in match and not isinstance(match["path"], list):
        raise TypeError("Persisted selection match 'path' must be a list")
    return deepcopy(match)


def syncSelectionState(
    renderer_interface: dict[str, Any],
    state: dict[str, Any],
    *,
    node_id: Any,
    renderer_id: Any,
) -> None:
    match = state.get("persistedSelectionMatch")
    if isinstance(match, dict) and match.get("id") == node_id:
        return

    state["persistedSelection"] = None
    state["persistedSelectionMatch"] = None
    state["lastSelectedElementID"] = node_id
    state["lastSelectedRendererID"] = (
        renderer_id if renderer_id is not None else renderer_interface.get("rendererID")
    )
    renderer_interface["setTrackedPath"](None)


def dispatchInspectScreenRequest(
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
    result = inspectScreenAcrossRenderers(
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
    from pyinkcli.packages.react_reconciler.ReactFiberReconciler import packageInfo

    return str(packageInfo["version"])


def inspectScreenAcrossRenderers(
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
                    inspected_screen = create_empty_inspected_screen(
                        inspected_roots.get("id", node_id),
                        inspected_roots.get("type", "root"),
                    )
                merge_inspected_roots(
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


def create_empty_inspected_screen(
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


def merge_inspected_roots(
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


__all__ = [
    "dispatchInspectScreenRequest",
    "inspectScreenAcrossRenderers",
    "normalizePersistedSelection",
    "normalizePersistedSelectionMatch",
    "create_empty_inspected_screen",
    "merge_inspected_roots",
    "package_version",
    "syncSelectionState",
]
