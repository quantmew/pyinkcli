"""Frontend-side helpers for hydrating devtools transport payloads."""

from __future__ import annotations

import inspect as inspect_module
from collections.abc import Callable, Iterable
from copy import deepcopy
from itertools import count
from typing import Any

META_KEY = "__devtools_meta__"
INSPECTED_KEY = "__devtools_inspected__"
UNSERIALIZABLE_KEY = "__devtools_unserializable__"
_VIRTUAL_METADATA_KEYS = {META_KEY, INSPECTED_KEY, UNSERIALIZABLE_KEY}
_BRIDGE_REQUEST_ID_COUNTER = count(1)


class _DevtoolsUndefinedType:
    def __repr__(self) -> str:
        return "undefined"


DEVTOOLS_UNDEFINED = _DevtoolsUndefinedType()


class SerializedMutationError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        partial_result: dict[str, Any],
        index: int,
        operation: dict[str, Any],
        cause: Exception,
    ) -> None:
        super().__init__(message)
        self.partial_result = partial_result
        self.index = index
        self.operation = operation
        self.cause = cause


def _serialize_batch_failure(
    *,
    index: int,
    operation: dict[str, Any],
    error: Exception,
) -> dict[str, Any]:
    return {
        "index": index,
        "operation": deepcopy(operation),
        "error_type": type(error).__name__,
        "error_message": str(error),
    }


class _DevtoolsMetadataMixin:
    _devtools_meta: dict[str, Any]
    _devtools_inspected: bool
    _devtools_unserializable: bool

    def _init_devtools_metadata(
        self,
        *,
        metadata: dict[str, Any],
        inspected: bool,
        unserializable: bool,
    ) -> None:
        self._devtools_meta = metadata
        self._devtools_inspected = inspected
        self._devtools_unserializable = unserializable

    def _get_virtual_key(self, key: str) -> Any:
        if key == META_KEY:
            return self._devtools_meta
        if key == INSPECTED_KEY:
            return self._devtools_inspected
        if key == UNSERIALIZABLE_KEY:
            return self._devtools_unserializable
        raise KeyError(key)

    def _set_virtual_key(self, key: str, value: Any) -> None:
        if key == META_KEY:
            self._devtools_meta = value
            return
        if key == INSPECTED_KEY:
            self._devtools_inspected = bool(value)
            return
        if key == UNSERIALIZABLE_KEY:
            self._devtools_unserializable = bool(value)
            return
        raise KeyError(key)


class HydratedDict(_DevtoolsMetadataMixin, dict):
    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, str) and key in _VIRTUAL_METADATA_KEYS:
            return self._get_virtual_key(key)
        return super().__getitem__(key)

    def __setitem__(self, key: Any, value: Any) -> None:
        if isinstance(key, str) and key in _VIRTUAL_METADATA_KEYS:
            self._set_virtual_key(key, value)
            return
        super().__setitem__(key, value)

    def get(self, key: Any, default: Any = None) -> Any:
        if isinstance(key, str) and key in _VIRTUAL_METADATA_KEYS:
            try:
                return self._get_virtual_key(key)
            except KeyError:
                return default
        return super().get(key, default)

    def __contains__(self, key: object) -> bool:
        if isinstance(key, str) and key in _VIRTUAL_METADATA_KEYS:
            return True
        return super().__contains__(key)

    def __deepcopy__(self, memo: dict[int, Any]) -> HydratedDict:
        copied = HydratedDict(deepcopy(dict(self), memo))
        copied._init_devtools_metadata(
            metadata=deepcopy(self._devtools_meta, memo),
            inspected=self._devtools_inspected,
            unserializable=self._devtools_unserializable,
        )
        return copied


class HydratedList(_DevtoolsMetadataMixin, list):
    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, str) and key in _VIRTUAL_METADATA_KEYS:
            return self._get_virtual_key(key)
        return super().__getitem__(key)

    def __setitem__(self, key: Any, value: Any) -> None:
        if isinstance(key, str) and key in _VIRTUAL_METADATA_KEYS:
            self._set_virtual_key(key, value)
            return
        super().__setitem__(key, value)

    def __contains__(self, item: object) -> bool:
        if isinstance(item, str) and item in _VIRTUAL_METADATA_KEYS:
            return True
        return super().__contains__(item)

    def __deepcopy__(self, memo: dict[int, Any]) -> HydratedList:
        copied = HydratedList(deepcopy(list(self), memo))
        copied._init_devtools_metadata(
            metadata=deepcopy(self._devtools_meta, memo),
            inspected=self._devtools_inspected,
            unserializable=self._devtools_unserializable,
        )
        return copied


def _has_virtual_metadata(value: Any) -> bool:
    return isinstance(value, (HydratedDict, HydratedList))


def has_metadata(value: Any) -> bool:
    if _has_virtual_metadata(value):
        return True
    return isinstance(value, dict) and META_KEY in value


def get_metadata(value: Any) -> dict[str, Any] | None:
    if _has_virtual_metadata(value):
        return value[META_KEY]
    if isinstance(value, dict):
        metadata = value.get(META_KEY)
        return metadata if isinstance(metadata, dict) else None
    return None


def set_metadata(value: Any, metadata: dict[str, Any]) -> Any:
    normalized = deepcopy(metadata)
    if _has_virtual_metadata(value):
        value[META_KEY] = normalized
        return value
    if isinstance(value, dict):
        value[META_KEY] = normalized
        return value
    raise TypeError("Metadata can only be set on hydrated containers or dict-like payloads")


def is_inspected(value: Any) -> bool:
    if _has_virtual_metadata(value):
        return bool(value[INSPECTED_KEY])
    if isinstance(value, dict):
        return bool(value.get(INSPECTED_KEY))
    return False


def mark_inspected(value: Any, inspected: bool = True) -> Any:
    if _has_virtual_metadata(value):
        value[INSPECTED_KEY] = inspected
        return value
    if isinstance(value, dict):
        value[INSPECTED_KEY] = bool(inspected)
        return value
    raise TypeError("Inspection state can only be set on hydrated containers or dict-like payloads")


def is_unserializable(value: Any) -> bool:
    if _has_virtual_metadata(value):
        return bool(value[UNSERIALIZABLE_KEY])
    if isinstance(value, dict):
        return bool(value.get(UNSERIALIZABLE_KEY))
    return False


def mark_unserializable(value: Any, unserializable: bool = True) -> Any:
    if _has_virtual_metadata(value):
        value[UNSERIALIZABLE_KEY] = unserializable
        return value
    if isinstance(value, dict):
        value[UNSERIALIZABLE_KEY] = bool(unserializable)
        return value
    raise TypeError("Unserializable state can only be set on hydrated containers or dict-like payloads")


def copy_with_metadata(value: Any) -> Any:
    return deepcopy(value)


def replace_metadata_value(target: Any, value: Any) -> Any:
    replacement = copy_with_metadata(value)
    if not has_metadata(target):
        return replacement

    metadata_source = replacement if has_metadata(replacement) else target
    metadata = get_metadata(metadata_source) or {}
    inspected = is_inspected(metadata_source)
    unserializable = is_unserializable(metadata_source)

    if isinstance(replacement, (dict, list)):
        return _create_metadata_container(
            replacement,
            metadata=metadata,
            inspected=inspected,
            unserializable=unserializable,
        )

    raise TypeError("Metadata-preserving replacement requires a dict- or list-like value")


def get_in_object(target: Any, path: list[Any]) -> Any:
    current = target
    for key in path:
        if isinstance(current, (list, tuple)):
            current = current[key]
            continue
        try:
            current = current[key]
            continue
        except (KeyError, TypeError, IndexError):
            if isinstance(key, int) and hasattr(current, "__iter__"):
                current = list(current)[key]
                continue
            raise
    return current


def set_in_object(target: Any, path: list[Any], value: Any) -> None:
    if not path:
        raise ValueError("Path must not be empty")
    current = get_in_object(target, path[:-1]) if len(path) > 1 else target
    current[path[-1]] = value


def delete_path_in_object(target: Any, path: list[Any]) -> None:
    if not path:
        raise ValueError("Path must not be empty")
    parent = get_in_object(target, path[:-1]) if len(path) > 1 else target
    key = path[-1]
    if isinstance(parent, list) and isinstance(key, int):
        parent.pop(key)
        return
    del parent[key]


def rename_path_in_object(
    target: Any,
    old_path: list[Any],
    new_path: list[Any],
) -> None:
    if not old_path or not new_path:
        raise ValueError("Paths must not be empty")
    if old_path == new_path:
        return

    old_parent = get_in_object(target, old_path[:-1]) if len(old_path) > 1 else target
    new_parent = get_in_object(target, new_path[:-1]) if len(new_path) > 1 else target
    old_key = old_path[-1]
    new_key = new_path[-1]

    if old_parent is new_parent and isinstance(old_parent, list):
        old_parent[new_key] = old_parent[old_key]
        old_parent.pop(old_key)
        return

    value = old_parent[old_key]
    new_parent[new_key] = value
    if isinstance(old_parent, list) and isinstance(old_key, int):
        old_parent.pop(old_key)
    else:
        del old_parent[old_key]


def _extract_transport_meta(node: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    metadata_keys = (
        "inspected",
        "inspectable",
        "name",
        "preview_long",
        "preview_short",
        "readonly",
        "size",
        "type",
        "unserializable",
    )
    metadata = {key: node[key] for key in metadata_keys if key in node}
    payload = {key: value for key, value in node.items() if key not in metadata_keys}
    return metadata, payload


def _restore_special_cleaned_value(node: Any) -> Any:
    if not isinstance(node, dict):
        return node
    node_type = node.get("type")
    if node_type == "infinity":
        return float("inf")
    if node_type == "nan":
        return float("nan")
    if node_type == "undefined":
        return DEVTOOLS_UNDEFINED
    return node


def _is_array_like_payload(payload: dict[str, Any]) -> bool:
    int_keys = sorted(key for key in payload if isinstance(key, int))
    if not int_keys:
        return False
    return int_keys == list(range(len(int_keys))) and len(int_keys) == len(payload)


def _create_metadata_container(
    payload: Any,
    *,
    metadata: dict[str, Any],
    inspected: bool,
    unserializable: bool,
) -> Any:
    if isinstance(payload, dict):
        if _is_array_like_payload(payload):
            container = HydratedList([payload[index] for index in range(len(payload))])
        else:
            container = HydratedDict(payload)
    elif isinstance(payload, list):
        container = HydratedList(payload)
    else:
        container = HydratedDict({})

    container._init_devtools_metadata(metadata={}, inspected=False, unserializable=False)
    set_metadata(container, metadata)
    mark_inspected(container, inspected)
    mark_unserializable(container, unserializable)
    return container


def _upgrade_cleaned_value(node: Any, *, inspected: bool = False) -> Any:
    restored = _restore_special_cleaned_value(node)
    if not isinstance(restored, dict):
        return restored
    metadata, _ = _extract_transport_meta(restored)
    return _create_metadata_container(
        {},
        metadata=metadata,
        inspected=inspected,
        unserializable=False,
    )


def _upgrade_unserializable_value(node: Any, *, inspected: bool | None = None) -> Any:
    if not isinstance(node, dict):
        return node
    metadata, payload = _extract_transport_meta(node)
    return _create_metadata_container(
        deepcopy(payload),
        metadata=metadata,
        inspected=(
            bool(metadata.get("inspected"))
            if inspected is None
            else inspected
        ),
        unserializable=True,
    )


def hydrate(
    data: Any,
    cleaned: Iterable[list[Any]],
    unserializable: Iterable[list[Any]],
) -> Any:
    hydrated = deepcopy(data)

    for path in cleaned:
        path_list = list(path)
        if not path_list:
            continue
        parent = get_in_object(hydrated, path_list[:-1]) if len(path_list) > 1 else hydrated
        key = path_list[-1]
        if isinstance(parent, dict) and key in parent or isinstance(parent, list) and isinstance(key, int) and 0 <= key < len(parent):
            parent[key] = _upgrade_cleaned_value(parent[key], inspected=False)

    for path in unserializable:
        path_list = list(path)
        if not path_list:
            continue
        parent = get_in_object(hydrated, path_list[:-1]) if len(path_list) > 1 else hydrated
        key = path_list[-1]
        if isinstance(parent, dict) and key in parent or isinstance(parent, list) and isinstance(key, int) and 0 <= key < len(parent):
            parent[key] = _upgrade_unserializable_value(parent[key], inspected=False)

    return hydrated


def hydrate_helper(
    dehydrated_data: dict[str, Any] | None,
    path: list[Any] | None = None,
) -> Any:
    if dehydrated_data is None:
        return None

    cleaned = list(dehydrated_data.get("cleaned", []))
    unserializable = list(dehydrated_data.get("unserializable", []))
    data = dehydrated_data.get("data")

    if path:
        path_length = len(path)
        cleaned = [cleaned_path[path_length:] for cleaned_path in cleaned]
        unserializable = [unserializable_path[path_length:] for unserializable_path in unserializable]

    has_root_cleaned = any(len(cleaned_path) == 0 for cleaned_path in cleaned)
    has_root_unserializable = any(len(unserializable_path) == 0 for unserializable_path in unserializable)
    cleaned = [cleaned_path for cleaned_path in cleaned if cleaned_path]
    unserializable = [unserializable_path for unserializable_path in unserializable if unserializable_path]

    hydrated = hydrate(data, cleaned, unserializable)

    if has_root_unserializable:
        return _upgrade_unserializable_value(hydrated, inspected=bool(path))
    if has_root_cleaned:
        return _upgrade_cleaned_value(hydrated, inspected=bool(path))

    return hydrated


def fill_in_path(target: Any, value: Any, path: list[Any]) -> Any:
    cloned = copy_with_metadata(target)
    set_in_object(cloned, path, value)
    return cloned


def delete_in_path(target: Any, path: list[Any]) -> Any:
    if not path:
        raise ValueError("Path must not be empty")
    cloned = copy_with_metadata(target)
    delete_path_in_object(cloned, path)
    return cloned


def rename_in_path(target: Any, old_path: list[Any], new_path: list[Any]) -> Any:
    if not old_path or not new_path:
        raise ValueError("Paths must not be empty")
    cloned = copy_with_metadata(target)
    rename_path_in_object(cloned, old_path, new_path)
    return cloned


def replace_in_path(target: Any, value: Any, path: list[Any]) -> Any:
    cloned = copy_with_metadata(target)
    if not path:
        return replace_metadata_value(cloned, value)

    current = get_in_object(cloned, path)
    replacement = replace_metadata_value(current, value) if has_metadata(current) else copy_with_metadata(value)
    set_in_object(cloned, path, replacement)
    return cloned


def update_in_path(target: Any, path: list[Any], updater: Callable[[Any], Any]) -> Any:
    cloned = copy_with_metadata(target)
    current = get_in_object(cloned, path) if path else cloned
    next_value = updater(current)
    if not path:
        if has_metadata(current):
            return replace_metadata_value(current, next_value)
        return copy_with_metadata(next_value)

    replacement = (
        replace_metadata_value(current, next_value)
        if has_metadata(current)
        else copy_with_metadata(next_value)
    )
    set_in_object(cloned, path, replacement)
    return cloned


def mutate_in_path(target: Any, path: list[Any], mutator: Callable[[Any], Any]) -> Any:
    cloned = copy_with_metadata(target)
    current = get_in_object(cloned, path) if path else cloned
    working_copy = copy_with_metadata(current)
    result = mutator(working_copy)
    next_value = working_copy if result is None else result

    if not path:
        if has_metadata(current):
            return replace_metadata_value(current, next_value)
        return copy_with_metadata(next_value)

    replacement = (
        replace_metadata_value(current, next_value)
        if has_metadata(current)
        else copy_with_metadata(next_value)
    )
    set_in_object(cloned, path, replacement)
    return cloned


def _get_serialized_mutation_value(operation: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in operation:
            return operation[key]
    return default


def normalize_serialized_mutation_bridge_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise TypeError("Serialized mutation bridge payload must be a dict")

    operations = payload.get("operations", [])
    if not isinstance(operations, list):
        raise TypeError("Serialized mutation bridge payload 'operations' must be a list")
    normalized_operations: list[dict[str, Any]] = []
    for operation in operations:
        if not isinstance(operation, dict):
            raise TypeError("Serialized mutation bridge payload operations must be dict items")
        normalized_operations.append(deepcopy(operation))

    mode = payload.get("mode", "fail-fast")
    if not isinstance(mode, str):
        raise TypeError("Serialized mutation bridge payload 'mode' must be a string")

    rollback = payload.get("rollback", False)
    if not isinstance(rollback, bool):
        raise TypeError("Serialized mutation bridge payload 'rollback' must be a bool")

    return {
        "operations": normalized_operations,
        "mode": mode,
        "rollback": rollback,
    }


def normalize_inspect_element_bridge_payload(
    payload: dict[str, Any] | None,
    *,
    request_id: Any = None,
) -> dict[str, Any]:
    return _normalize_inspect_bridge_payload(
        payload,
        request_id=request_id,
        payload_name="Inspect element bridge payload",
        include_renderer_id=True,
    )


def normalize_inspect_screen_bridge_payload(
    payload: dict[str, Any] | None,
    *,
    request_id: Any = None,
) -> dict[str, Any]:
    return _normalize_inspect_bridge_payload(
        payload,
        request_id=request_id,
        payload_name="Inspect screen bridge payload",
        include_renderer_id=False,
    )


def _normalize_inspect_bridge_payload(
    payload: dict[str, Any] | None,
    *,
    request_id: Any = None,
    payload_name: str,
    include_renderer_id: bool,
) -> dict[str, Any]:
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise TypeError(f"{payload_name} must be a dict")

    node_id = payload.get("id")
    if node_id is None:
        raise ValueError(f"{payload_name} must include 'id'")

    path = payload.get("path")
    if path is not None and not isinstance(path, list):
        raise TypeError(f"{payload_name} 'path' must be a list or None")

    force_full_data = payload.get("forceFullData", False)
    if not isinstance(force_full_data, bool):
        raise TypeError(f"{payload_name} 'forceFullData' must be a bool")

    renderer_id = payload.get("rendererID") if include_renderer_id else None
    payload_request_id = payload.get("requestID", payload.get("requestId", request_id))
    if payload_request_id is None:
        raise ValueError(f"{payload_name} must include requestID or envelope requestId")

    return {
        "id": node_id,
        "path": list(path) if isinstance(path, list) else None,
        "forceFullData": force_full_data,
        "rendererID": renderer_id,
        "requestID": payload_request_id,
    }


def normalize_clear_errors_and_warnings_bridge_payload(
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    return _normalize_devtools_notification_payload(
        payload,
        payload_name="Clear errors and warnings bridge payload",
        require_renderer_id=True,
    )


def normalize_clear_errors_for_element_bridge_payload(
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    return _normalize_devtools_notification_payload(
        payload,
        payload_name="Clear errors for element bridge payload",
        require_renderer_id=True,
        require_id=True,
    )


def normalize_clear_warnings_for_element_bridge_payload(
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    return _normalize_devtools_notification_payload(
        payload,
        payload_name="Clear warnings for element bridge payload",
        require_renderer_id=True,
        require_id=True,
    )


def normalize_copy_element_path_bridge_payload(
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    return _normalize_devtools_notification_payload(
        payload,
        payload_name="Copy element path bridge payload",
        require_renderer_id=True,
        require_id=True,
        require_path=True,
    )


def normalize_store_as_global_bridge_payload(
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    return _normalize_devtools_notification_payload(
        payload,
        payload_name="Store as global bridge payload",
        require_renderer_id=True,
        require_id=True,
        require_path=True,
        require_count=True,
    )


def normalize_log_element_to_console_bridge_payload(
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    return _normalize_devtools_notification_payload(
        payload,
        payload_name="Log element to console bridge payload",
        require_renderer_id=True,
        require_id=True,
    )


def normalize_override_suspense_milestone_bridge_payload(
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = _normalize_devtools_notification_payload(
        payload,
        payload_name="Override suspense milestone bridge payload",
        require_renderer_id=True,
    )
    suspended_set = {} if payload is None else payload
    value = suspended_set.get("suspendedSet")
    if not isinstance(value, list):
        raise TypeError("Override suspense milestone bridge payload 'suspendedSet' must be a list")
    normalized["suspendedSet"] = list(value)
    return normalized


def _normalize_devtools_notification_payload(
    payload: dict[str, Any] | None,
    *,
    payload_name: str,
    require_renderer_id: bool = False,
    require_id: bool = False,
    require_path: bool = False,
    require_count: bool = False,
) -> dict[str, Any]:
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise TypeError(f"{payload_name} must be a dict")

    normalized: dict[str, Any] = {}

    if require_renderer_id:
        if "rendererID" not in payload:
            raise ValueError(f"{payload_name} must include 'rendererID'")
        normalized["rendererID"] = payload["rendererID"]

    if require_id:
        if "id" not in payload:
            raise ValueError(f"{payload_name} must include 'id'")
        normalized["id"] = payload["id"]

    if require_path:
        path = payload.get("path")
        if not isinstance(path, list):
            raise TypeError(f"{payload_name} 'path' must be a list")
        normalized["path"] = list(path)

    if require_count:
        if "count" not in payload:
            raise ValueError(f"{payload_name} must include 'count'")
        normalized["count"] = payload["count"]

    return normalized


def _invoke_inspect_element_handler(
    inspector: Callable[..., Any],
    *,
    request_id: Any,
    node_id: Any,
    path: list[Any] | None,
    force_full_data: bool,
    renderer_id: Any,
) -> Any:
    signature = inspect_module.signature(inspector)
    params = signature.parameters
    if "renderer_id" in params:
        return inspector(
            request_id=request_id,
            node_id=node_id,
            path=path,
            force_full_data=force_full_data,
            renderer_id=renderer_id,
        )
    if "rendererID" in params:
        return inspector(
            request_id=request_id,
            node_id=node_id,
            path=path,
            force_full_data=force_full_data,
            rendererID=renderer_id,
        )
    if len(params) >= 5:
        return inspector(request_id, node_id, path, force_full_data, renderer_id)
    return inspector(request_id, node_id, path, force_full_data)


def apply_serialized_mutation(target: Any, operation: dict[str, Any]) -> Any:
    op = _get_serialized_mutation_value(operation, "op", "type", "kind")
    if not isinstance(op, str):
        raise ValueError("Serialized mutation must include an 'op' string")

    normalized_op = op.lower()
    path = list(_get_serialized_mutation_value(operation, "path", default=[]))

    if normalized_op == "set":
        value = _get_serialized_mutation_value(operation, "value")
        if path:
            return fill_in_path(target, value, path)
        return replace_in_path(target, value, [])

    if normalized_op == "delete":
        if not path:
            raise ValueError("Delete mutation requires a non-empty path")
        return delete_in_path(target, path)

    if normalized_op == "rename":
        old_path = list(_get_serialized_mutation_value(operation, "old_path", "oldPath", default=[]))
        new_path = list(_get_serialized_mutation_value(operation, "new_path", "newPath", default=[]))
        return rename_in_path(target, old_path, new_path)

    if normalized_op == "replace":
        return replace_in_path(target, _get_serialized_mutation_value(operation, "value"), path)

    if normalized_op == "update":
        updater = _get_serialized_mutation_value(operation, "updater", "value")
        if not callable(updater):
            raise TypeError("Update mutation requires a callable 'updater'")
        return update_in_path(target, path, updater)

    if normalized_op == "mutate":
        mutator = _get_serialized_mutation_value(operation, "mutator", "value")
        if not callable(mutator):
            raise TypeError("Mutate mutation requires a callable 'mutator'")
        return mutate_in_path(target, path, mutator)

    raise ValueError(f"Unsupported serialized mutation op: {op}")


def apply_serialized_mutations(
    target: Any,
    operations: Iterable[dict[str, Any]],
    *,
    mode: str = "fail-fast",
    rollback: bool = False,
) -> dict[str, Any]:
    normalized_mode = mode.lower()
    if normalized_mode not in {"fail-fast", "best-effort"}:
        raise ValueError("Batch mutation mode must be 'fail-fast' or 'best-effort'")
    if not isinstance(rollback, bool):
        raise TypeError("Batch mutation rollback flag must be a bool")

    baseline = copy_with_metadata(target)
    current = copy_with_metadata(target)
    errors: list[dict[str, Any]] = []
    applied = 0
    applied_indices: list[int] = []
    failed_indices: list[int] = []

    for index, operation in enumerate(operations):
        try:
            current = apply_serialized_mutation(current, operation)
            applied += 1
            applied_indices.append(index)
        except Exception as error:
            failed_indices.append(index)
            error_entry = _serialize_batch_failure(
                index=index,
                operation=operation,
                error=error,
            )
            if normalized_mode == "fail-fast":
                rolled_back = rollback
                partial_result = {
                    "value": baseline if rolled_back else current,
                    "errors": [error_entry],
                    "mode": normalized_mode,
                    "applied": applied,
                    "applied_indices": applied_indices,
                    "failed_indices": failed_indices,
                    "rolled_back": rolled_back,
                }
                raise SerializedMutationError(
                    f"Serialized mutation failed at index {index}: {error}",
                    partial_result=partial_result,
                    index=index,
                    operation=deepcopy(operation),
                    cause=error,
                ) from error
            errors.append(error_entry)

    rolled_back = rollback and bool(errors)
    final_value = baseline if rolled_back else current

    return {
        "value": final_value,
        "errors": errors,
        "mode": normalized_mode,
        "applied": applied,
        "applied_indices": applied_indices,
        "failed_indices": failed_indices,
        "rolled_back": rolled_back,
    }


def serialize_serialized_mutation_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "value": copy_with_metadata(result["value"]),
        "errors": deepcopy(result.get("errors", [])),
        "mode": result["mode"],
        "applied": result["applied"],
        "applied_indices": list(result.get("applied_indices", [])),
        "failed_indices": list(result.get("failed_indices", [])),
        "rolled_back": bool(result.get("rolled_back", False)),
        "failure": None,
    }


def serialize_serialized_mutation_error(error: SerializedMutationError) -> dict[str, Any]:
    partial_result = error.partial_result
    return {
        "ok": False,
        "value": copy_with_metadata(partial_result["value"]),
        "errors": deepcopy(partial_result.get("errors", [])),
        "mode": partial_result["mode"],
        "applied": partial_result["applied"],
        "applied_indices": list(partial_result.get("applied_indices", [])),
        "failed_indices": list(partial_result.get("failed_indices", [])),
        "rolled_back": bool(partial_result.get("rolled_back", False)),
        "failure": _serialize_batch_failure(
            index=error.index,
            operation=error.operation,
            error=error.cause,
        ),
    }


def serialize_serialized_mutation_outcome(
    outcome: dict[str, Any] | SerializedMutationError,
) -> dict[str, Any]:
    if isinstance(outcome, SerializedMutationError):
        return serialize_serialized_mutation_error(outcome)
    return serialize_serialized_mutation_result(outcome)


def make_serialized_mutation_bridge_handler(
    target: Any | Callable[[], Any],
) -> Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]:
    def handler(payload: dict[str, Any], _message: dict[str, Any]) -> dict[str, Any]:
        normalized = normalize_serialized_mutation_bridge_payload(payload)
        current_target = target() if callable(target) else target
        return apply_serialized_mutations(
            current_target,
            normalized["operations"],
            mode=normalized["mode"],
            rollback=normalized["rollback"],
        )

    return handler


def make_inspect_element_bridge_handler(
    inspector: Callable[..., dict[str, Any]],
) -> Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]:
    return _make_inspect_bridge_handler(
        inspector,
        normalizer=normalize_inspect_element_bridge_payload,
        result_label="Inspect element bridge handler",
    )


def make_inspect_screen_bridge_handler(
    inspector: Callable[..., dict[str, Any]],
) -> Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]:
    return _make_inspect_bridge_handler(
        inspector,
        normalizer=normalize_inspect_screen_bridge_payload,
        result_label="Inspect screen bridge handler",
    )


def _make_inspect_bridge_handler(
    inspector: Callable[..., dict[str, Any]],
    *,
    normalizer: Callable[..., dict[str, Any]],
    result_label: str,
) -> Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]:
    def handler(payload: dict[str, Any], message: dict[str, Any]) -> dict[str, Any]:
        normalized = normalizer(
            payload,
            request_id=message.get("requestId"),
        )
        result = _invoke_inspect_element_handler(
            inspector,
            request_id=normalized["requestID"],
            node_id=normalized["id"],
            path=normalized["path"],
            force_full_data=normalized["forceFullData"],
            renderer_id=normalized["rendererID"],
        )
        if not isinstance(result, dict):
            raise TypeError(f"{result_label} must return a dict payload")
        response = deepcopy(result)
        response.setdefault("responseID", normalized["requestID"])
        response.setdefault("id", normalized["id"])
        return response

    return handler


def make_clear_errors_and_warnings_bridge_handler(
    handler: Callable[..., Any],
) -> Callable[[dict[str, Any], dict[str, Any]], Any]:
    return _make_notification_bridge_handler(
        handler,
        normalizer=normalize_clear_errors_and_warnings_bridge_payload,
    )


def make_clear_errors_for_element_bridge_handler(
    handler: Callable[..., Any],
) -> Callable[[dict[str, Any], dict[str, Any]], Any]:
    return _make_notification_bridge_handler(
        handler,
        normalizer=normalize_clear_errors_for_element_bridge_payload,
    )


def make_clear_warnings_for_element_bridge_handler(
    handler: Callable[..., Any],
) -> Callable[[dict[str, Any], dict[str, Any]], Any]:
    return _make_notification_bridge_handler(
        handler,
        normalizer=normalize_clear_warnings_for_element_bridge_payload,
    )


def make_copy_element_path_bridge_handler(
    handler: Callable[..., Any],
) -> Callable[[dict[str, Any], dict[str, Any]], Any]:
    return _make_notification_bridge_handler(
        handler,
        normalizer=normalize_copy_element_path_bridge_payload,
    )


def make_store_as_global_bridge_handler(
    handler: Callable[..., Any],
) -> Callable[[dict[str, Any], dict[str, Any]], Any]:
    return _make_notification_bridge_handler(
        handler,
        normalizer=normalize_store_as_global_bridge_payload,
    )


def make_log_element_to_console_bridge_handler(
    handler: Callable[..., Any],
) -> Callable[[dict[str, Any], dict[str, Any]], Any]:
    return _make_notification_bridge_handler(
        handler,
        normalizer=normalize_log_element_to_console_bridge_payload,
    )


def make_override_suspense_milestone_bridge_handler(
    handler: Callable[..., Any],
) -> Callable[[dict[str, Any], dict[str, Any]], Any]:
    return _make_notification_bridge_handler(
        handler,
        normalizer=normalize_override_suspense_milestone_bridge_payload,
    )


def _make_notification_bridge_handler(
    handler: Callable[..., Any],
    *,
    normalizer: Callable[[dict[str, Any] | None], dict[str, Any]],
) -> Callable[[dict[str, Any], dict[str, Any]], Any]:
    def wrapped(payload: dict[str, Any], message: dict[str, Any]) -> Any:
        normalized = normalizer(payload)
        return handler(normalized, message)

    return wrapped


def serialize_bridge_message_envelope(
    payload: dict[str, Any],
    *,
    event: str,
    message_type: str = "response",
    request_id: Any = None,
) -> dict[str, Any]:
    if not isinstance(event, str) or not event:
        raise ValueError("Bridge message event must be a non-empty string")
    if not isinstance(message_type, str) or not message_type:
        raise ValueError("Bridge message type must be a non-empty string")

    envelope = {
        "event": event,
        "type": message_type,
        "payload": deepcopy(payload),
    }
    if request_id is not None:
        envelope["requestId"] = deepcopy(request_id)
    return envelope


def _next_bridge_request_id() -> int:
    return next(_BRIDGE_REQUEST_ID_COUNTER)


def make_bridge_request(
    event: str,
    payload: dict[str, Any],
    *,
    request_id: Any = None,
) -> dict[str, Any]:
    return serialize_bridge_message_envelope(
        payload,
        event=event,
        message_type="request",
        request_id=_next_bridge_request_id() if request_id is None else request_id,
    )


def make_bridge_call(
    event: str,
    payload: dict[str, Any],
    *,
    request_id: Any = None,
) -> dict[str, Any]:
    return make_bridge_request(
        event,
        payload,
        request_id=request_id,
    )


def make_bridge_notification(
    event: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return serialize_bridge_message_envelope(
        payload,
        event=event,
        message_type="notification",
    )


def make_bridge_response(
    event: str,
    payload: dict[str, Any],
    *,
    request_id: Any = None,
) -> dict[str, Any]:
    return serialize_bridge_message_envelope(
        payload,
        event=event,
        message_type="response",
        request_id=_next_bridge_request_id() if request_id is None else request_id,
    )


def make_bridge_success_response(
    event: str,
    payload: dict[str, Any] | None = None,
    *,
    request_id: Any = None,
) -> dict[str, Any]:
    response_payload = dict(payload or {})
    response_payload["ok"] = True
    response_payload["failure"] = None
    return make_bridge_response(
        event,
        response_payload,
        request_id=request_id,
    )


def make_bridge_error_response(
    event: str,
    failure: dict[str, Any],
    payload: dict[str, Any] | None = None,
    *,
    request_id: Any = None,
) -> dict[str, Any]:
    response_payload = dict(payload or {})
    response_payload["ok"] = False
    response_payload["failure"] = deepcopy(failure)
    return make_bridge_response(
        event,
        response_payload,
        request_id=request_id,
    )


def serialize_serialized_mutation_message(
    outcome: dict[str, Any] | SerializedMutationError,
    *,
    event: str = "serialized-mutation",
    request_id: Any = None,
) -> dict[str, Any]:
    payload = serialize_serialized_mutation_outcome(outcome)
    base_payload = {key: deepcopy(value) for key, value in payload.items() if key not in {"ok", "failure"}}
    if payload["ok"]:
        return make_bridge_success_response(
            event,
            base_payload,
            request_id=request_id,
        )
    return make_bridge_error_response(
        event,
        payload["failure"],
        base_payload,
        request_id=request_id,
    )


def _normalize_bridge_call_result(result: Any) -> tuple[bool, dict[str, Any], dict[str, Any] | None]:
    if result is None:
        return True, {}, None
    if isinstance(result, dict):
        if "ok" in result or "failure" in result:
            ok = bool(result.get("ok"))
            failure = deepcopy(result.get("failure"))
            payload = {key: deepcopy(value) for key, value in result.items() if key not in {"ok", "failure"}}
            return ok, payload, failure
        return True, deepcopy(result), None
    return True, {"value": deepcopy(result)}, None


def _serialize_bridge_call_error(error: Exception) -> dict[str, Any]:
    if isinstance(error, SerializedMutationError):
        return serialize_serialized_mutation_error(error)
    return {
        "ok": False,
        "value": None,
        "errors": [],
        "mode": "fail-fast",
        "applied": 0,
        "applied_indices": [],
        "failed_indices": [],
        "rolled_back": False,
        "failure": {
            "error_type": type(error).__name__,
            "error_message": str(error),
        },
    }


def handle_bridge_call(
    message: dict[str, Any],
    handlers: dict[str, Callable[..., Any]],
) -> dict[str, Any]:
    if not isinstance(message, dict):
        raise TypeError("Bridge call message must be a dict")
    if message.get("type") != "request":
        raise ValueError("Bridge call message must have type='request'")
    event = message.get("event")
    if not isinstance(event, str) or not event:
        raise ValueError("Bridge call message must include a non-empty event")
    if "requestId" not in message:
        raise ValueError("Bridge call message must include requestId")

    payload = message.get("payload", {})
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise TypeError("Bridge call payload must be a dict")

    handler = handlers.get(event)
    if handler is None:
        return make_bridge_error_response(
            event,
            {
                "error_type": "LookupError",
                "error_message": f'No bridge call handler registered for "{event}"',
            },
            request_id=message["requestId"],
        )

    try:
        result = handler(payload, message)
        ok, response_payload, failure = _normalize_bridge_call_result(result)
        if ok:
            return make_bridge_success_response(
                event,
                response_payload,
                request_id=message["requestId"],
            )
        return make_bridge_error_response(
            event,
            failure or {"error_type": "RuntimeError", "error_message": "Unknown bridge call failure"},
            response_payload,
            request_id=message["requestId"],
        )
    except Exception as error:
        serialized = _serialize_bridge_call_error(error)
        response_payload = {key: deepcopy(value) for key, value in serialized.items() if key not in {"ok", "failure"}}
        return make_bridge_error_response(
            event,
            serialized["failure"],
            response_payload,
            request_id=message["requestId"],
        )


def dispatch_bridge_message(
    message: dict[str, Any],
    *,
    call_handlers: dict[str, Callable[..., Any]] | None = None,
    notification_handlers: dict[str, Callable[..., Any]] | None = None,
) -> Any:
    if not isinstance(message, dict):
        raise TypeError("Bridge message must be a dict")

    message_type = message.get("type")
    if message_type == "request":
        return handle_bridge_call(message, call_handlers or {})

    if message_type == "notification":
        event = message.get("event")
        if not isinstance(event, str) or not event:
            raise ValueError("Bridge notification must include a non-empty event")
        payload = message.get("payload", {})
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            raise TypeError("Bridge notification payload must be a dict")
        handler = (notification_handlers or {}).get(event)
        if handler is None:
            return None
        return handler(payload, message)

    raise ValueError("Bridge message type must be 'request' or 'notification'")


def handle_serialized_mutation_bridge_call(
    message: dict[str, Any],
    target: Any | Callable[[], Any],
    *,
    event: str = "devtools:mutation",
) -> dict[str, Any]:
    return handle_bridge_call(
        message,
        {event: make_serialized_mutation_bridge_handler(target)},
    )


def handle_inspect_element_bridge_call(
    message: dict[str, Any],
    inspector: Callable[..., dict[str, Any]],
    *,
    event: str = "inspectElement",
    response_event: str = "inspectedElement",
) -> dict[str, Any]:
    return _handle_inspect_bridge_call(
        message,
        inspector,
        event=event,
        response_event=response_event,
        normalizer=normalize_inspect_element_bridge_payload,
        handler_factory=make_inspect_element_bridge_handler,
    )


def handle_inspect_screen_bridge_call(
    message: dict[str, Any],
    inspector: Callable[..., dict[str, Any]],
    *,
    event: str = "inspectScreen",
    response_event: str = "inspectedScreen",
) -> dict[str, Any]:
    return _handle_inspect_bridge_call(
        message,
        inspector,
        event=event,
        response_event=response_event,
        normalizer=normalize_inspect_screen_bridge_payload,
        handler_factory=make_inspect_screen_bridge_handler,
    )


def _handle_inspect_bridge_call(
    message: dict[str, Any],
    inspector: Callable[..., dict[str, Any]],
    *,
    event: str,
    response_event: str,
    normalizer: Callable[..., dict[str, Any]],
    handler_factory: Callable[[Callable[..., dict[str, Any]]], Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]],
) -> dict[str, Any]:
    if not isinstance(message, dict):
        raise TypeError("Bridge call message must be a dict")
    if message.get("type") != "request":
        raise ValueError("Bridge call message must have type='request'")
    if "requestId" not in message:
        raise ValueError("Bridge call message must include requestId")
    if message.get("event") != event:
        raise ValueError(f"Bridge call message event must be '{event}'")

    payload = message.get("payload", {})
    if payload is None:
        payload = {}
    normalized = normalizer(
        payload,
        request_id=message["requestId"],
    )

    try:
        response_payload = handler_factory(inspector)(normalized, message)
        return make_bridge_success_response(
            response_event,
            response_payload,
            request_id=message["requestId"],
        )
    except Exception as error:
        serialized = _serialize_bridge_call_error(error)
        response_payload = {key: deepcopy(value) for key, value in serialized.items() if key not in {"ok", "failure"}}
        return make_bridge_error_response(
            response_event,
            serialized["failure"],
            response_payload,
            request_id=message["requestId"],
        )


def handle_bridge_notification(
    message: dict[str, Any],
    handler: Callable[[dict[str, Any], dict[str, Any]], Any],
    *,
    event: str,
    normalizer: Callable[[dict[str, Any] | None], dict[str, Any]],
) -> Any:
    if not isinstance(message, dict):
        raise TypeError("Bridge notification message must be a dict")
    if message.get("type") != "notification":
        raise ValueError("Bridge notification message must have type='notification'")
    if message.get("event") != event:
        raise ValueError(f"Bridge notification message event must be '{event}'")

    payload = message.get("payload", {})
    if payload is None:
        payload = {}
    normalized = normalizer(payload)
    return handler(normalized, message)


def handle_clear_errors_and_warnings_bridge_notification(
    message: dict[str, Any],
    handler: Callable[[dict[str, Any], dict[str, Any]], Any],
    *,
    event: str = "clearErrorsAndWarnings",
) -> Any:
    return handle_bridge_notification(
        message,
        handler,
        event=event,
        normalizer=normalize_clear_errors_and_warnings_bridge_payload,
    )


def handle_clear_errors_for_element_bridge_notification(
    message: dict[str, Any],
    handler: Callable[[dict[str, Any], dict[str, Any]], Any],
    *,
    event: str = "clearErrorsForElementID",
) -> Any:
    return handle_bridge_notification(
        message,
        handler,
        event=event,
        normalizer=normalize_clear_errors_for_element_bridge_payload,
    )


def handle_clear_warnings_for_element_bridge_notification(
    message: dict[str, Any],
    handler: Callable[[dict[str, Any], dict[str, Any]], Any],
    *,
    event: str = "clearWarningsForElementID",
) -> Any:
    return handle_bridge_notification(
        message,
        handler,
        event=event,
        normalizer=normalize_clear_warnings_for_element_bridge_payload,
    )


def handle_copy_element_path_bridge_notification(
    message: dict[str, Any],
    handler: Callable[[dict[str, Any], dict[str, Any]], Any],
    *,
    event: str = "copyElementPath",
) -> Any:
    return handle_bridge_notification(
        message,
        handler,
        event=event,
        normalizer=normalize_copy_element_path_bridge_payload,
    )


def handle_store_as_global_bridge_notification(
    message: dict[str, Any],
    handler: Callable[[dict[str, Any], dict[str, Any]], Any],
    *,
    event: str = "storeAsGlobal",
) -> Any:
    return handle_bridge_notification(
        message,
        handler,
        event=event,
        normalizer=normalize_store_as_global_bridge_payload,
    )


def handle_log_element_to_console_bridge_notification(
    message: dict[str, Any],
    handler: Callable[[dict[str, Any], dict[str, Any]], Any],
    *,
    event: str = "logElementToConsole",
) -> Any:
    return handle_bridge_notification(
        message,
        handler,
        event=event,
        normalizer=normalize_log_element_to_console_bridge_payload,
    )


def handle_override_suspense_milestone_bridge_notification(
    message: dict[str, Any],
    handler: Callable[[dict[str, Any], dict[str, Any]], Any],
    *,
    event: str = "overrideSuspenseMilestone",
) -> Any:
    return handle_bridge_notification(
        message,
        handler,
        event=event,
        normalizer=normalize_override_suspense_milestone_bridge_payload,
    )


def make_devtools_backend_notification_handlers(
    *,
    clear_errors_and_warnings: Callable[[dict[str, Any], dict[str, Any]], Any] | None = None,
    clear_errors_for_element: Callable[[dict[str, Any], dict[str, Any]], Any] | None = None,
    clear_warnings_for_element: Callable[[dict[str, Any], dict[str, Any]], Any] | None = None,
    copy_element_path: Callable[[dict[str, Any], dict[str, Any]], Any] | None = None,
    store_as_global: Callable[[dict[str, Any], dict[str, Any]], Any] | None = None,
    log_element_to_console: Callable[[dict[str, Any], dict[str, Any]], Any] | None = None,
    override_suspense_milestone: Callable[[dict[str, Any], dict[str, Any]], Any] | None = None,
) -> dict[str, Callable[[dict[str, Any], dict[str, Any]], Any]]:
    handlers: dict[str, Callable[[dict[str, Any], dict[str, Any]], Any]] = {}
    if clear_errors_and_warnings is not None:
        handlers["clearErrorsAndWarnings"] = make_clear_errors_and_warnings_bridge_handler(
            clear_errors_and_warnings
        )
    if clear_errors_for_element is not None:
        handlers["clearErrorsForElementID"] = make_clear_errors_for_element_bridge_handler(
            clear_errors_for_element
        )
    if clear_warnings_for_element is not None:
        handlers["clearWarningsForElementID"] = make_clear_warnings_for_element_bridge_handler(
            clear_warnings_for_element
        )
    if copy_element_path is not None:
        handlers["copyElementPath"] = make_copy_element_path_bridge_handler(copy_element_path)
    if store_as_global is not None:
        handlers["storeAsGlobal"] = make_store_as_global_bridge_handler(store_as_global)
    if log_element_to_console is not None:
        handlers["logElementToConsole"] = make_log_element_to_console_bridge_handler(
            log_element_to_console
        )
    if override_suspense_milestone is not None:
        handlers["overrideSuspenseMilestone"] = make_override_suspense_milestone_bridge_handler(
            override_suspense_milestone
        )
    return handlers


getInObject = get_in_object
setInObject = set_in_object
deletePathInObject = delete_path_in_object
renamePathInObject = rename_path_in_object
fillInPath = fill_in_path
replaceInPath = replace_in_path
updateInPath = update_in_path
mutateInPath = mutate_in_path
applySerializedMutation = apply_serialized_mutation
applySerializedMutations = apply_serialized_mutations
serializeSerializedMutationResult = serialize_serialized_mutation_result
serializeSerializedMutationError = serialize_serialized_mutation_error
serializeSerializedMutationOutcome = serialize_serialized_mutation_outcome
serializeBridgeMessageEnvelope = serialize_bridge_message_envelope
serializeSerializedMutationMessage = serialize_serialized_mutation_message
normalizeSerializedMutationBridgePayload = normalize_serialized_mutation_bridge_payload
normalizeInspectElementBridgePayload = normalize_inspect_element_bridge_payload
normalizeInspectScreenBridgePayload = normalize_inspect_screen_bridge_payload
normalizeClearErrorsAndWarningsBridgePayload = normalize_clear_errors_and_warnings_bridge_payload
normalizeClearErrorsForElementBridgePayload = normalize_clear_errors_for_element_bridge_payload
normalizeClearWarningsForElementBridgePayload = normalize_clear_warnings_for_element_bridge_payload
normalizeCopyElementPathBridgePayload = normalize_copy_element_path_bridge_payload
normalizeLogElementToConsoleBridgePayload = normalize_log_element_to_console_bridge_payload
normalizeOverrideSuspenseMilestoneBridgePayload = normalize_override_suspense_milestone_bridge_payload
normalizeStoreAsGlobalBridgePayload = normalize_store_as_global_bridge_payload
makeSerializedMutationBridgeHandler = make_serialized_mutation_bridge_handler
makeInspectElementBridgeHandler = make_inspect_element_bridge_handler
makeInspectScreenBridgeHandler = make_inspect_screen_bridge_handler
makeClearErrorsAndWarningsBridgeHandler = make_clear_errors_and_warnings_bridge_handler
makeClearErrorsForElementBridgeHandler = make_clear_errors_for_element_bridge_handler
makeClearWarningsForElementBridgeHandler = make_clear_warnings_for_element_bridge_handler
makeCopyElementPathBridgeHandler = make_copy_element_path_bridge_handler
makeLogElementToConsoleBridgeHandler = make_log_element_to_console_bridge_handler
makeOverrideSuspenseMilestoneBridgeHandler = make_override_suspense_milestone_bridge_handler
makeStoreAsGlobalBridgeHandler = make_store_as_global_bridge_handler
makeDevtoolsBackendNotificationHandlers = make_devtools_backend_notification_handlers
makeBridgeSuccessResponse = make_bridge_success_response
makeBridgeErrorResponse = make_bridge_error_response
makeBridgeRequest = make_bridge_request
makeBridgeCall = make_bridge_call
makeBridgeNotification = make_bridge_notification
makeBridgeResponse = make_bridge_response
handleBridgeCall = handle_bridge_call
handleSerializedMutationBridgeCall = handle_serialized_mutation_bridge_call
handleInspectElementBridgeCall = handle_inspect_element_bridge_call
handleInspectScreenBridgeCall = handle_inspect_screen_bridge_call
handleBridgeNotification = handle_bridge_notification
handleClearErrorsAndWarningsBridgeNotification = handle_clear_errors_and_warnings_bridge_notification
handleClearErrorsForElementBridgeNotification = handle_clear_errors_for_element_bridge_notification
handleClearWarningsForElementBridgeNotification = handle_clear_warnings_for_element_bridge_notification
handleCopyElementPathBridgeNotification = handle_copy_element_path_bridge_notification
handleLogElementToConsoleBridgeNotification = handle_log_element_to_console_bridge_notification
handleOverrideSuspenseMilestoneBridgeNotification = handle_override_suspense_milestone_bridge_notification
handleStoreAsGlobalBridgeNotification = handle_store_as_global_bridge_notification
dispatchBridgeMessage = dispatch_bridge_message
hasMetadata = has_metadata
getMetadata = get_metadata
setMetadata = set_metadata
isInspected = is_inspected
markInspected = mark_inspected
isUnserializable = is_unserializable
markUnserializable = mark_unserializable
copyWithMetadata = copy_with_metadata
replaceMetadataValue = replace_metadata_value


__all__ = [
    "DEVTOOLS_UNDEFINED",
    "META_KEY",
    "INSPECTED_KEY",
    "UNSERIALIZABLE_KEY",
    "SerializedMutationError",
    "HydratedDict",
    "HydratedList",
    "delete_in_path",
    "delete_path_in_object",
    "deletePathInObject",
    "copy_with_metadata",
    "copyWithMetadata",
    "apply_serialized_mutation",
    "applySerializedMutation",
    "apply_serialized_mutations",
    "applySerializedMutations",
    "make_bridge_request",
    "makeBridgeRequest",
    "make_bridge_call",
    "makeBridgeCall",
    "make_bridge_notification",
    "makeBridgeNotification",
    "make_bridge_response",
    "makeBridgeResponse",
    "make_bridge_success_response",
    "makeBridgeSuccessResponse",
    "make_bridge_error_response",
    "makeBridgeErrorResponse",
    "serialize_bridge_message_envelope",
    "serializeBridgeMessageEnvelope",
    "serialize_serialized_mutation_result",
    "serializeSerializedMutationResult",
    "serialize_serialized_mutation_error",
    "serializeSerializedMutationError",
    "serialize_serialized_mutation_outcome",
    "serializeSerializedMutationOutcome",
    "serialize_serialized_mutation_message",
    "serializeSerializedMutationMessage",
    "fill_in_path",
    "fillInPath",
    "handle_bridge_call",
    "handleBridgeCall",
    "handle_bridge_notification",
    "handleBridgeNotification",
    "handle_clear_errors_and_warnings_bridge_notification",
    "handleClearErrorsAndWarningsBridgeNotification",
    "handle_clear_errors_for_element_bridge_notification",
    "handleClearErrorsForElementBridgeNotification",
    "handle_clear_warnings_for_element_bridge_notification",
    "handleClearWarningsForElementBridgeNotification",
    "handle_copy_element_path_bridge_notification",
    "handleCopyElementPathBridgeNotification",
    "handle_log_element_to_console_bridge_notification",
    "handleLogElementToConsoleBridgeNotification",
    "handle_override_suspense_milestone_bridge_notification",
    "handleOverrideSuspenseMilestoneBridgeNotification",
    "handle_inspect_element_bridge_call",
    "handleInspectElementBridgeCall",
    "handle_inspect_screen_bridge_call",
    "handleInspectScreenBridgeCall",
    "handle_serialized_mutation_bridge_call",
    "handleSerializedMutationBridgeCall",
    "handle_store_as_global_bridge_notification",
    "handleStoreAsGlobalBridgeNotification",
    "getMetadata",
    "get_metadata",
    "get_in_object",
    "getInObject",
    "hasMetadata",
    "has_metadata",
    "dispatch_bridge_message",
    "dispatchBridgeMessage",
    "hydrate",
    "hydrate_helper",
    "isInspected",
    "is_inspected",
    "isUnserializable",
    "is_unserializable",
    "markInspected",
    "markUnserializable",
    "mark_inspected",
    "mark_unserializable",
    "make_clear_errors_and_warnings_bridge_handler",
    "makeClearErrorsAndWarningsBridgeHandler",
    "make_clear_errors_for_element_bridge_handler",
    "makeClearErrorsForElementBridgeHandler",
    "make_clear_warnings_for_element_bridge_handler",
    "makeClearWarningsForElementBridgeHandler",
    "make_copy_element_path_bridge_handler",
    "makeCopyElementPathBridgeHandler",
    "make_log_element_to_console_bridge_handler",
    "makeLogElementToConsoleBridgeHandler",
    "make_override_suspense_milestone_bridge_handler",
    "makeOverrideSuspenseMilestoneBridgeHandler",
    "make_devtools_backend_notification_handlers",
    "makeDevtoolsBackendNotificationHandlers",
    "make_serialized_mutation_bridge_handler",
    "makeSerializedMutationBridgeHandler",
    "make_inspect_element_bridge_handler",
    "makeInspectElementBridgeHandler",
    "make_inspect_screen_bridge_handler",
    "makeInspectScreenBridgeHandler",
    "make_store_as_global_bridge_handler",
    "makeStoreAsGlobalBridgeHandler",
    "mutate_in_path",
    "mutateInPath",
    "normalize_clear_errors_and_warnings_bridge_payload",
    "normalizeClearErrorsAndWarningsBridgePayload",
    "normalize_clear_errors_for_element_bridge_payload",
    "normalizeClearErrorsForElementBridgePayload",
    "normalize_clear_warnings_for_element_bridge_payload",
    "normalizeClearWarningsForElementBridgePayload",
    "normalize_copy_element_path_bridge_payload",
    "normalizeCopyElementPathBridgePayload",
    "normalize_log_element_to_console_bridge_payload",
    "normalizeLogElementToConsoleBridgePayload",
    "normalize_override_suspense_milestone_bridge_payload",
    "normalizeOverrideSuspenseMilestoneBridgePayload",
    "normalize_inspect_element_bridge_payload",
    "normalizeInspectElementBridgePayload",
    "normalize_inspect_screen_bridge_payload",
    "normalizeInspectScreenBridgePayload",
    "normalize_serialized_mutation_bridge_payload",
    "normalizeSerializedMutationBridgePayload",
    "normalize_store_as_global_bridge_payload",
    "normalizeStoreAsGlobalBridgePayload",
    "replace_metadata_value",
    "replaceMetadataValue",
    "replace_in_path",
    "replaceInPath",
    "rename_in_path",
    "rename_path_in_object",
    "renamePathInObject",
    "setMetadata",
    "set_metadata",
    "set_in_object",
    "setInObject",
    "update_in_path",
    "updateInPath",
]
