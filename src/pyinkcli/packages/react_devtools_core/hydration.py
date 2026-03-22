from __future__ import annotations

from copy import deepcopy
from itertools import count
from typing import Any, Callable, Iterable

META_KEY = "__ink_devtools_meta__"
INSPECTED_KEY = "__ink_devtools_inspected__"
UNSERIALIZABLE_KEY = "__ink_devtools_unserializable__"


class HydratedDict(dict):
    pass


class HydratedList(list):
    pass


class _UndefinedType:
    def __repr__(self) -> str:  # pragma: no cover - trivial
        return "undefined"


DEVTOOLS_UNDEFINED = _UndefinedType()


class SerializedMutationError(RuntimeError):
    def __init__(
        self,
        index: int,
        operation: dict[str, Any],
        cause: Exception,
        partial_result: dict[str, Any],
    ) -> None:
        super().__init__(f"Serialized mutation failed at index {index}")
        self.index = index
        self.operation = operation
        self.cause = cause
        self.partial_result = partial_result


_request_ids = count(1)

_TRANSPORT_META_KEYS = {
    "type",
    "name",
    "preview_short",
    "preview_long",
    "inspectable",
    "readonly",
    "size",
    "unserializable",
}


def _deep_clone(value: Any) -> Any:
    if isinstance(value, HydratedDict):
        clone = HydratedDict()
        for key, item in value.items():
            clone[key] = _deep_clone(item)
        _copy_hidden_metadata(value, clone)
        return clone
    if isinstance(value, HydratedList):
        clone = HydratedList(_deep_clone(item) for item in value)
        _copy_hidden_metadata(value, clone)
        return clone
    if isinstance(value, dict):
        return {key: _deep_clone(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_deep_clone(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_deep_clone(item) for item in value)
    try:
        return deepcopy(value)
    except Exception:  # pragma: no cover - defensive
        return value


def _copy_hidden_metadata(source: Any, target: Any) -> None:
    metadata = getattr(source, "_ink_metadata", None)
    if metadata is not None:
        target._ink_metadata = dict(metadata)
    if hasattr(source, "_ink_inspected"):
        target._ink_inspected = bool(getattr(source, "_ink_inspected"))
    if hasattr(source, "_ink_unserializable"):
        target._ink_unserializable = bool(getattr(source, "_ink_unserializable"))


def _is_wrapper(value: Any) -> bool:
    return isinstance(value, (HydratedDict, HydratedList))


def _legacy_metadata(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict) and META_KEY in value:
        metadata = value[META_KEY]
        return dict(metadata) if isinstance(metadata, dict) else None
    return None


def _metadata(value: Any) -> dict[str, Any] | None:
    metadata = getattr(value, "_ink_metadata", None)
    if metadata is not None:
        return dict(metadata)
    return _legacy_metadata(value)


def has_metadata(value: Any) -> bool:
    return _metadata(value) is not None


def get_metadata(value: Any) -> dict[str, Any] | None:
    return _metadata(value)


def set_metadata(value: Any, metadata: dict[str, Any]) -> Any:
    if _is_wrapper(value):
        value._ink_metadata = dict(metadata)
        return value
    if isinstance(value, dict):
        value[META_KEY] = dict(metadata)
        return value
    raise TypeError("set_metadata expects a dict-like hydrated value")


def mark_inspected(value: Any, inspected: bool = True) -> Any:
    if _is_wrapper(value):
        value._ink_inspected = bool(inspected)
        return value
    if isinstance(value, dict):
        value[INSPECTED_KEY] = bool(inspected)
        return value
    raise TypeError("mark_inspected expects a dict-like hydrated value")


def mark_unserializable(value: Any, unserializable: bool = True) -> Any:
    if _is_wrapper(value):
        value._ink_unserializable = bool(unserializable)
        return value
    if isinstance(value, dict):
        value[UNSERIALIZABLE_KEY] = bool(unserializable)
        return value
    raise TypeError("mark_unserializable expects a dict-like hydrated value")


def is_inspected(value: Any) -> bool:
    if _is_wrapper(value):
        return bool(getattr(value, "_ink_inspected", False))
    if isinstance(value, dict):
        return bool(value.get(INSPECTED_KEY, False))
    return False


def is_unserializable(value: Any) -> bool:
    if _is_wrapper(value):
        return bool(getattr(value, "_ink_unserializable", False))
    if isinstance(value, dict):
        return bool(value.get(UNSERIALIZABLE_KEY, False))
    return False


def copy_with_metadata(value: Any) -> Any:
    return _deep_clone(value)


def copyWithMetadata(value: Any) -> Any:
    return copy_with_metadata(value)


def replace_metadata_value(source: Any, new_value: Any) -> Any:
    replacement = _deep_clone(new_value)
    metadata = _metadata(source)
    if metadata is None:
        return replacement
    if isinstance(replacement, list):
        wrapper: Any = HydratedList(replacement)
    elif isinstance(replacement, dict):
        wrapper = HydratedDict(replacement)
    else:
        return replacement
    set_metadata(wrapper, metadata)
    if _is_wrapper(source):
        if hasattr(source, "_ink_inspected"):
            mark_inspected(wrapper, is_inspected(source))
        if hasattr(source, "_ink_unserializable"):
            mark_unserializable(wrapper, is_unserializable(source))
    else:
        if isinstance(source, dict):
            if INSPECTED_KEY in source:
                mark_inspected(wrapper, bool(source.get(INSPECTED_KEY)))
            if UNSERIALIZABLE_KEY in source:
                mark_unserializable(wrapper, bool(source.get(UNSERIALIZABLE_KEY)))
    return wrapper


def replaceMetadataValue(source: Any, new_value: Any) -> Any:
    return replace_metadata_value(source, new_value)


def _path_list(path: Iterable[Any] | None) -> list[Any]:
    return list(path or [])


def get_in_object(object_: Any, path: Iterable[Any]) -> Any:
    current = object_
    for key in path:
        if isinstance(current, (dict, HydratedDict)) and key in current:
            current = current[key]
        elif isinstance(current, (list, HydratedList)) and isinstance(key, int) and 0 <= key < len(current):
            current = current[key]
        else:
            return None
    return current


def getInObject(object_: Any, path: Iterable[Any]) -> Any:
    return get_in_object(object_, path)


def _set_at_path(target: Any, path: list[Any], value: Any) -> Any:
    if not path:
        return value

    parent = target
    for key in path[:-1]:
        if isinstance(parent, (dict, HydratedDict)):
            parent = parent[key]
        elif isinstance(parent, (list, HydratedList)):
            parent = parent[key]
        else:  # pragma: no cover - defensive
            raise TypeError("Cannot traverse non-container value")

    last = path[-1]
    if isinstance(parent, (list, HydratedList)) and isinstance(last, int):
        if last == len(parent):
            parent.append(value)
        else:
            parent[last] = value
    else:
        parent[last] = value
    return target


def set_in_object(object_: Any, path: Iterable[Any], value: Any) -> Any:
    replacement = _deep_clone(value)
    return _set_at_path(object_, _path_list(path), replacement)


def setInObject(object_: Any, path: Iterable[Any], value: Any) -> Any:
    return set_in_object(object_, path, value)


def delete_path_in_object(object_: Any, path: Iterable[Any]) -> Any:
    parts = _path_list(path)
    if not parts:
        return object_
    parent = get_in_object(object_, parts[:-1])
    if parent is None:
        return object_
    last = parts[-1]
    if isinstance(parent, (list, HydratedList)) and isinstance(last, int):
        if 0 <= last < len(parent):
            del parent[last]
    elif isinstance(parent, dict):
        parent.pop(last, None)
    return object_


def deletePathInObject(object_: Any, path: Iterable[Any]) -> Any:
    return delete_path_in_object(object_, path)


def delete_in_path(object_: Any, path: Iterable[Any]) -> Any:
    clone = _deep_clone(object_)
    return delete_path_in_object(clone, path)


def rename_path_in_object(object_: Any, old_path: Iterable[Any], new_path: Iterable[Any]) -> Any:
    old_parts = _path_list(old_path)
    new_parts = _path_list(new_path)
    if old_parts == new_parts:
        return object_
    value = get_in_object(object_, old_parts)
    if value is None:
        return object_
    delete_path_in_object(object_, old_parts)
    _set_at_path(object_, new_parts, _deep_clone(value))
    return object_


def renamePathInObject(object_: Any, old_path: Iterable[Any], new_path: Iterable[Any]) -> Any:
    return rename_path_in_object(object_, old_path, new_path)


def rename_in_path(object_: Any, old_path: Iterable[Any], new_path: Iterable[Any]) -> Any:
    clone = _deep_clone(object_)
    return rename_path_in_object(clone, old_path, new_path)


def replace_in_path(object_: Any, value: Any, path: Iterable[Any]) -> Any:
    clone = _deep_clone(object_)
    parts = _path_list(path)
    if not parts:
        if has_metadata(clone):
            return replace_metadata_value(clone, value)
        return _deep_clone(value)
    current = get_in_object(clone, parts)
    replacement = replace_metadata_value(current, value) if has_metadata(current) else _deep_clone(value)
    return _set_at_path(clone, parts, replacement)


def replaceInPath(object_: Any, value: Any, path: Iterable[Any]) -> Any:
    return replace_in_path(object_, value, path)


def update_in_path(object_: Any, path: Iterable[Any], updater: Callable[[Any], Any]) -> Any:
    if not callable(updater):
        raise TypeError("update_in_path expects a callable updater")
    clone = _deep_clone(object_)
    parts = _path_list(path)
    current = get_in_object(clone, parts)
    replacement = updater(_deep_clone(current))
    if has_metadata(current):
        replacement = replace_metadata_value(current, replacement)
    return _set_at_path(clone, parts, replacement)


def updateInPath(object_: Any, path: Iterable[Any], updater: Callable[[Any], Any]) -> Any:
    return update_in_path(object_, path, updater)


def mutate_in_path(object_: Any, path: Iterable[Any], mutator: Callable[[Any], Any]) -> Any:
    if not callable(mutator):
        raise TypeError("mutate_in_path expects a callable mutator")
    clone = _deep_clone(object_)
    parts = _path_list(path)
    target = get_in_object(clone, parts)
    mutator(target)
    return clone


def mutateInPath(object_: Any, path: Iterable[Any], mutator: Callable[[Any], Any]) -> Any:
    return mutate_in_path(object_, path, mutator)


def fill_in_path(object_: Any, value: Any, path: Iterable[Any]) -> Any:
    clone = _deep_clone(object_)
    return set_in_object(clone, path, value)


def fillInPath(object_: Any, value: Any, path: Iterable[Any]) -> Any:
    return fill_in_path(object_, value, path)


def _transport_metadata(data: dict[str, Any]) -> dict[str, Any]:
    metadata = {}
    for key in _TRANSPORT_META_KEYS:
        if key in data:
            metadata[key] = data[key]
    return metadata


def _hydrate_transport_value(value: Any, path: list[Any], cleaned: set[tuple[Any, ...]], unserializable: set[tuple[Any, ...]]) -> Any:
    path_tuple = tuple(path)
    if isinstance(value, dict) and "type" in value:
        value_type = value["type"]
        if value_type == "infinity":
            return float("inf")
        if value_type == "nan":
            return float("nan")
        if value_type == "undefined":
            return DEVTOOLS_UNDEFINED

        metadata = _transport_metadata(value)
        if value_type in {"array", "iterator", "typed_array", "html_all_collection"}:
            items = []
            for key in sorted(k for k in value.keys() if isinstance(k, int)):
                items.append(_hydrate_transport_value(value[key], path + [key], cleaned, unserializable))
            hydrated = HydratedList(items)
        else:
            hydrated = HydratedDict()
            for key, item in value.items():
                if key in _TRANSPORT_META_KEYS:
                    continue
                hydrated[key] = _hydrate_transport_value(item, path + [key], cleaned, unserializable)

        if metadata:
            set_metadata(hydrated, metadata)
        if path_tuple in unserializable or bool(value.get("unserializable")):
            mark_unserializable(hydrated, True)
        else:
            mark_unserializable(hydrated, False)
        mark_inspected(hydrated, False)
        return hydrated

    if isinstance(value, dict):
        hydrated_dict = HydratedDict()
        for key, item in value.items():
            hydrated_dict[key] = _hydrate_transport_value(item, path + [key], cleaned, unserializable)
        return hydrated_dict

    if isinstance(value, list):
        hydrated_list = HydratedList()
        for index, item in enumerate(value):
            hydrated_list.append(_hydrate_transport_value(item, path + [index], cleaned, unserializable))
        return hydrated_list

    return value


def hydrate(object_: dict[str, Any], cleaned: list[list[Any]], unserializable: list[list[Any]]) -> Any:
    cleaned_set = {tuple(path) for path in cleaned}
    unserializable_set = {tuple(path) for path in unserializable}
    hydrated = _hydrate_transport_value(object_["data"], [], cleaned_set, unserializable_set)
    for path in cleaned_set:
        node = get_in_object(hydrated, path)
        if node is not None and isinstance(node, (dict, HydratedDict, list, HydratedList)):
            if path in unserializable_set:
                mark_unserializable(node, True)
    return hydrated


def hydrate_helper(payload: Any, path: list[Any] | None = None) -> Any:
    if isinstance(payload, dict) and "data" in payload and "cleaned" in payload and "unserializable" in payload:
        cleaned_paths = payload.get("cleaned", [])
        unserializable_paths = payload.get("unserializable", [])
        if path is not None:
            path_prefix = list(path)

            def _strip_prefix(entries: list[list[Any]]) -> list[list[Any]]:
                normalized: list[list[Any]] = []
                for entry in entries:
                    if entry[: len(path_prefix)] == path_prefix:
                        normalized.append(entry[len(path_prefix) :])
                    else:
                        normalized.append(entry)
                return normalized

            cleaned_paths = _strip_prefix(cleaned_paths)
            unserializable_paths = _strip_prefix(unserializable_paths)

        hydrated = hydrate(payload, cleaned_paths, unserializable_paths)
        if path is not None and isinstance(hydrated, (dict, list, HydratedDict, HydratedList)):
            mark_inspected(hydrated, True)
        return hydrated
    clone = _deep_clone(payload)
    if path is not None and isinstance(clone, (dict, list, HydratedDict, HydratedList)):
        mark_inspected(clone, True)
    return clone


def isInspected(value: Any) -> bool:
    return is_inspected(value)


def isUnserializable(value: Any) -> bool:
    return is_unserializable(value)


def hasMetadata(value: Any) -> bool:
    return has_metadata(value)


def getMetadata(value: Any) -> dict[str, Any] | None:
    return get_metadata(value)


def setMetadata(value: Any, metadata: dict[str, Any]) -> Any:
    return set_metadata(value, metadata)


def markInspected(value: Any, inspected: bool = True) -> Any:
    return mark_inspected(value, inspected)


def markUnserializable(value: Any, unserializable: bool = True) -> Any:
    return mark_unserializable(value, unserializable)


def _normalize_dict(payload: Any, label: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError(f"{label} must be a dict")
    return dict(payload)


def _require_bool(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key, False)
    if not isinstance(value, bool):
        raise TypeError(f"'{key}' must be a bool")
    return value


def _require_list(payload: dict[str, Any], key: str, *, label: str | None = None) -> list[Any]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        raise TypeError(label or f"'{key}' must be a list")
    return list(value)


def normalize_clear_errors_and_warnings_bridge_payload(payload: Any) -> dict[str, Any]:
    data = _normalize_dict(payload, "payload")
    if "rendererID" not in data:
        raise ValueError("payload must include 'rendererID'")
    return {"rendererID": data["rendererID"]}


def normalizeClearErrorsAndWarningsBridgePayload(payload: Any) -> dict[str, Any]:
    return normalize_clear_errors_and_warnings_bridge_payload(payload)


def normalize_clear_errors_for_element_bridge_payload(payload: Any) -> dict[str, Any]:
    data = _normalize_dict(payload, "payload")
    if "rendererID" not in data:
        raise ValueError("payload must include 'rendererID'")
    if "id" not in data:
        raise ValueError("payload must include 'id'")
    return {"rendererID": data["rendererID"], "id": data["id"]}


def normalizeClearErrorsForElementBridgePayload(payload: Any) -> dict[str, Any]:
    return normalize_clear_errors_for_element_bridge_payload(payload)


def normalize_copy_element_path_bridge_payload(payload: Any) -> dict[str, Any]:
    data = _normalize_dict(payload, "payload")
    if "rendererID" not in data:
        raise ValueError("payload must include 'rendererID'")
    if "id" not in data:
        raise ValueError("payload must include 'id'")
    path = data.get("path", [])
    if not isinstance(path, list):
        raise TypeError("'path' must be a list")
    return {"rendererID": data["rendererID"], "id": data["id"], "path": list(path)}


def normalizeCopyElementPathBridgePayload(payload: Any) -> dict[str, Any]:
    return normalize_copy_element_path_bridge_payload(payload)


def normalize_store_as_global_bridge_payload(payload: Any) -> dict[str, Any]:
    data = _normalize_dict(payload, "payload")
    if "rendererID" not in data:
        raise ValueError("payload must include 'rendererID'")
    if "id" not in data:
        raise ValueError("payload must include 'id'")
    path = data.get("path", [])
    if not isinstance(path, list):
        raise TypeError("'path' must be a list")
    count_value = data.get("count", 0)
    if not isinstance(count_value, int):
        raise TypeError("'count' must be an int")
    return {
        "rendererID": data["rendererID"],
        "id": data["id"],
        "path": list(path),
        "count": count_value,
    }


def normalizeStoreAsGlobalBridgePayload(payload: Any) -> dict[str, Any]:
    return normalize_store_as_global_bridge_payload(payload)


def normalize_override_suspense_milestone_bridge_payload(payload: Any) -> dict[str, Any]:
    data = _normalize_dict(payload, "payload")
    if "rendererID" not in data:
        raise ValueError("payload must include 'rendererID'")
    suspended = data.get("suspendedSet", [])
    if not isinstance(suspended, list):
        raise TypeError("'suspendedSet' must be a list")
    return {"rendererID": data["rendererID"], "suspendedSet": list(suspended)}


def normalizeOverrideSuspenseMilestoneBridgePayload(payload: Any) -> dict[str, Any]:
    return normalize_override_suspense_milestone_bridge_payload(payload)


def normalize_inspect_element_bridge_payload(payload: Any, request_id: Any | None = None) -> dict[str, Any]:
    data = _normalize_dict(payload, "payload")
    if "id" not in data:
        raise ValueError("payload must include 'id'")
    path = data.get("path")
    if path is not None and not isinstance(path, list):
        raise TypeError("'path' must be a list or None")
    force_full_data = data.get("forceFullData", False)
    if not isinstance(force_full_data, bool):
        raise TypeError("'forceFullData' must be a bool")
    return {
        "id": data["id"],
        "path": None if path is None else list(path),
        "forceFullData": force_full_data,
        "rendererID": data.get("rendererID"),
        "requestID": request_id,
    }


def normalizeInspectElementBridgePayload(payload: Any, request_id: Any | None = None) -> dict[str, Any]:
    return normalize_inspect_element_bridge_payload(payload, request_id=request_id)


def normalize_inspect_screen_bridge_payload(payload: Any, request_id: Any | None = None) -> dict[str, Any]:
    data = _normalize_dict(payload, "payload")
    if "id" not in data:
        raise ValueError("payload must include 'id'")
    path = data.get("path")
    if path is not None and not isinstance(path, list):
        raise TypeError("'path' must be a list or None")
    force_full_data = data.get("forceFullData", False)
    if not isinstance(force_full_data, bool):
        raise TypeError("'forceFullData' must be a bool")
    return {
        "id": data["id"],
        "path": None if path is None else list(path),
        "forceFullData": force_full_data,
        "rendererID": data.get("rendererID"),
        "requestID": request_id,
    }


def normalizeInspectScreenBridgePayload(payload: Any, request_id: Any | None = None) -> dict[str, Any]:
    return normalize_inspect_screen_bridge_payload(payload, request_id=request_id)


def normalize_serialized_mutation_bridge_payload(payload: Any) -> dict[str, Any]:
    data = _normalize_dict(payload, "payload")
    operations = data.get("operations", [])
    if not isinstance(operations, list):
        raise TypeError("'operations' must be a list")
    normalized_ops = []
    for item in operations:
        if not isinstance(item, dict):
            raise TypeError("operations must contain dict items")
        normalized_ops.append(dict(item))
    mode = data.get("mode", "fail-fast")
    if not isinstance(mode, str):
        raise TypeError("'mode' must be a string")
    rollback = data.get("rollback", False)
    if not isinstance(rollback, bool):
        raise TypeError("'rollback' must be a bool")
    return {"operations": normalized_ops, "mode": mode, "rollback": rollback}


def normalizeSerializedMutationBridgePayload(payload: Any) -> dict[str, Any]:
    return normalize_serialized_mutation_bridge_payload(payload)


def _bridge_envelope(payload: Any, event: str, message_type: str, request_id: Any | None = None) -> dict[str, Any]:
    if not event:
        raise ValueError("event must be a non-empty string")
    if not message_type:
        raise ValueError("type must be a non-empty string")
    message = {"event": event, "type": message_type, "payload": _deep_clone(payload)}
    if request_id is not None:
        if not isinstance(request_id, (int, str)):
            raise TypeError("requestId must be an int or string")
        message["requestId"] = request_id
    return message


def serialize_bridge_message_envelope(
    payload: Any,
    *,
    event: str,
    message_type: str = "response",
    request_id: Any | None = None,
) -> dict[str, Any]:
    return _bridge_envelope(payload, event, message_type, request_id=request_id)


def serializeBridgeMessageEnvelope(
    payload: Any,
    *,
    event: str,
    message_type: str = "response",
    request_id: Any | None = None,
) -> dict[str, Any]:
    return serialize_bridge_message_envelope(
        payload, event=event, message_type=message_type, request_id=request_id
    )


def make_bridge_request(event: str, payload: Any, request_id: Any | None = None) -> dict[str, Any]:
    if request_id is None:
        request_id = next(_request_ids)
    if request_id is not None and not isinstance(request_id, (int, str)):
        raise TypeError("requestId must be an int or string")
    return _bridge_envelope(payload, event, "request", request_id=request_id)


def makeBridgeRequest(event: str, payload: Any, request_id: Any | None = None) -> dict[str, Any]:
    return make_bridge_request(event, payload, request_id=request_id)


def make_bridge_call(event: str, payload: Any, request_id: Any | None = None) -> dict[str, Any]:
    return make_bridge_request(event, payload, request_id=request_id)


def makeBridgeCall(event: str, payload: Any, request_id: Any | None = None) -> dict[str, Any]:
    return make_bridge_call(event, payload, request_id=request_id)


def make_bridge_notification(event: str, payload: Any) -> dict[str, Any]:
    return _bridge_envelope(payload, event, "notification")


def makeBridgeNotification(event: str, payload: Any) -> dict[str, Any]:
    return make_bridge_notification(event, payload)


def make_bridge_response(event: str, payload: Any, request_id: Any | None = None) -> dict[str, Any]:
    if request_id is None:
        request_id = next(_request_ids)
    return _bridge_envelope(payload, event, "response", request_id=request_id)


def makeBridgeResponse(event: str, payload: Any, request_id: Any | None = None) -> dict[str, Any]:
    return make_bridge_response(event, payload, request_id=request_id)


def make_bridge_success_response(
    event: str,
    payload: dict[str, Any],
    request_id: Any | None = None,
) -> dict[str, Any]:
    response_payload = {"ok": True, "failure": None, **_deep_clone(payload)}
    return make_bridge_response(event, response_payload, request_id=request_id)


def makeBridgeSuccessResponse(
    event: str,
    payload: dict[str, Any],
    request_id: Any | None = None,
) -> dict[str, Any]:
    return make_bridge_success_response(event, payload, request_id=request_id)


def make_bridge_error_response(
    event: str,
    failure: dict[str, Any],
    payload: dict[str, Any],
    request_id: Any | None = None,
) -> dict[str, Any]:
    response_payload = {"ok": False, "failure": _deep_clone(failure), **_deep_clone(payload)}
    return make_bridge_response(event, response_payload, request_id=request_id)


def makeBridgeErrorResponse(
    event: str,
    failure: dict[str, Any],
    payload: dict[str, Any],
    request_id: Any | None = None,
) -> dict[str, Any]:
    return make_bridge_error_response(event, failure, payload, request_id=request_id)


def _serialized_mutation_result_payload(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "failure": None,
        "mode": result["mode"],
        "applied": result["applied"],
        "applied_indices": list(result["applied_indices"]),
        "failed_indices": list(result["failed_indices"]),
        "rolled_back": result["rolled_back"],
        "errors": _deep_clone(result["errors"]),
        "value": _deep_clone(result["value"]),
    }


def serialize_serialized_mutation_result(result: dict[str, Any]) -> dict[str, Any]:
    return _serialized_mutation_result_payload(result)


def serializeSerializedMutationResult(result: dict[str, Any]) -> dict[str, Any]:
    return serialize_serialized_mutation_result(result)


def serialize_serialized_mutation_error(error: SerializedMutationError) -> dict[str, Any]:
    payload = _serialized_mutation_result_payload(error.partial_result)
    payload["ok"] = False
    payload["failure"] = {
        "index": error.index,
        "operation": _deep_clone(error.operation),
        "error_type": type(error.cause).__name__,
        "error_message": str(error.cause),
    }
    return payload


def serializeSerializedMutationError(error: SerializedMutationError) -> dict[str, Any]:
    return serialize_serialized_mutation_error(error)


def serialize_serialized_mutation_outcome(
    result_or_error: dict[str, Any] | SerializedMutationError,
) -> dict[str, Any]:
    if isinstance(result_or_error, SerializedMutationError):
        return serialize_serialized_mutation_error(result_or_error)
    return serialize_serialized_mutation_result(result_or_error)


def serializeSerializedMutationOutcome(
    result_or_error: dict[str, Any] | SerializedMutationError,
) -> dict[str, Any]:
    return serialize_serialized_mutation_outcome(result_or_error)


def serialize_serialized_mutation_message(
    result_or_error: dict[str, Any] | SerializedMutationError,
    *,
    event: str,
    request_id: Any | None = None,
) -> dict[str, Any]:
    return serialize_bridge_message_envelope(
        serialize_serialized_mutation_outcome(result_or_error),
        event=event,
        request_id=request_id,
    )


def serializeSerializedMutationMessage(
    result_or_error: dict[str, Any] | SerializedMutationError,
    *,
    event: str,
    request_id: Any | None = None,
) -> dict[str, Any]:
    return serialize_serialized_mutation_message(result_or_error, event=event, request_id=request_id)


def _mutation_partial_result(
    original: Any,
    working: Any,
    mode: str,
    applied: list[int],
    failed: list[int],
    errors: list[dict[str, Any]],
    rolled_back: bool,
    rollback: bool,
) -> dict[str, Any]:
    return {
        "mode": mode,
        "applied": len(applied),
        "applied_indices": list(applied),
        "failed_indices": list(failed),
        "rolled_back": rolled_back,
        "errors": _deep_clone(errors),
        "value": _deep_clone(original if rolled_back else working),
    }


def apply_serialized_mutation(object_: Any, operation: dict[str, Any]) -> Any:
    if not isinstance(operation, dict):
        raise TypeError("operation must be a dict")
    if "op" not in operation:
        raise ValueError("Serialized mutation operations must include an 'op'")

    op = operation["op"]
    if op == "set":
        path = operation.get("path")
        if not path:
            raise ValueError("Serialized mutation operations require a non-empty path")
        return set_in_object(object_, path, operation.get("value"))

    if op == "delete":
        path = operation.get("path")
        if not path:
            raise ValueError("Serialized mutation operations require a non-empty path")
        return delete_path_in_object(object_, path)

    if op == "rename":
        old_path = operation.get("oldPath")
        new_path = operation.get("newPath")
        if not old_path or not new_path:
            raise ValueError("Serialized mutation rename operations require both paths")
        return rename_path_in_object(object_, old_path, new_path)

    if op == "replace":
        path = operation.get("path")
        if path is None:
            raise ValueError("Serialized mutation operations require a path")
        return replace_in_path(object_, operation.get("value"), path)

    if op == "update":
        path = operation.get("path")
        if path is None:
            raise ValueError("Serialized mutation operations require a path")
        updater = operation.get("updater")
        if not callable(updater):
            raise TypeError("Serialized mutation update operations require a callable 'updater'")
        return update_in_path(object_, path, updater)

    if op == "mutate":
        path = operation.get("path")
        if path is None:
            raise ValueError("Serialized mutation operations require a path")
        mutator = operation.get("mutator")
        if not callable(mutator):
            raise TypeError("Serialized mutation mutate operations require a callable 'mutator'")
        return mutate_in_path(object_, path, mutator)

    raise ValueError(f"Unsupported serialized mutation op: {op}")


def applySerializedMutation(object_: Any, operation: dict[str, Any]) -> Any:
    return apply_serialized_mutation(object_, operation)


def apply_serialized_mutations(
    object_: Any,
    operations: list[dict[str, Any]],
    *,
    mode: str = "fail-fast",
    rollback: bool = False,
) -> dict[str, Any]:
    if not isinstance(operations, list):
        raise TypeError("operations must be a list")
    if mode not in {"fail-fast", "best-effort"}:
        raise ValueError("Batch mutation mode must be 'fail-fast' or 'best-effort'")
    if not isinstance(rollback, bool):
        raise TypeError("rollback flag must be a bool")

    original = _deep_clone(object_)
    working = _deep_clone(object_)
    applied: list[int] = []
    failed: list[int] = []
    errors: list[dict[str, Any]] = []

    for index, operation in enumerate(operations):
        try:
            working = apply_serialized_mutation(working, operation)
            applied.append(index)
        except Exception as error:
            failed.append(index)
            error_record = {
                "index": index,
                "operation": _deep_clone(operation),
                "error_type": type(error).__name__,
                "error_message": str(error),
            }
            errors.append(error_record)
            if mode == "fail-fast":
                rolled_back = bool(rollback)
                partial_result = _mutation_partial_result(
                    original,
                    working,
                    mode,
                    applied,
                    failed,
                    errors,
                    rolled_back,
                    rollback,
                )
                raise SerializedMutationError(index, operation, error, partial_result) from error

    rolled_back = bool(rollback and errors)
    result_value = original if rolled_back else working
    return {
        "mode": mode,
        "applied": len(applied),
        "applied_indices": list(applied),
        "failed_indices": list(failed),
        "rolled_back": rolled_back,
        "errors": _deep_clone(errors),
        "value": _deep_clone(result_value),
    }


def applySerializedMutations(
    object_: Any,
    operations: list[dict[str, Any]],
    *,
    mode: str = "fail-fast",
    rollback: bool = False,
) -> dict[str, Any]:
    return apply_serialized_mutations(object_, operations, mode=mode, rollback=rollback)


def make_serialized_mutation_bridge_handler(target: Any | Callable[[], Any]):
    def handler(payload: Any, _message: Any):
        normalized = normalize_serialized_mutation_bridge_payload(payload)
        live_target = target() if callable(target) else target
        return apply_serialized_mutations(
            live_target,
            normalized["operations"],
            mode=normalized["mode"],
            rollback=normalized["rollback"],
        )

    return handler


def makeSerializedMutationBridgeHandler(target: Any | Callable[[], Any]):
    return make_serialized_mutation_bridge_handler(target)


def handle_bridge_call(
    message: Any,
    call_handlers: dict[str, Callable[[Any, Any], Any]],
) -> dict[str, Any]:
    if not isinstance(message, dict):
        raise TypeError("message must be a dict")
    if message.get("type") != "request":
        raise ValueError("Bridge message must have type='request'")
    if "event" not in message:
        raise ValueError("Bridge request must include an event")
    if "requestId" not in message:
        raise ValueError("Bridge request must include requestId")
    if not isinstance(message.get("payload"), dict):
        raise TypeError("Bridge request payload must be a dict")
    if not isinstance(message.get("requestId"), (int, str)):
        raise TypeError("requestId must be an int or string")

    event = message["event"]
    handler = call_handlers.get(event)
    if handler is None:
        failure = {"error_type": "LookupError", "error_message": f"Unknown event: {event}"}
        return make_bridge_error_response(event, failure, {"value": None}, request_id=message["requestId"])

    try:
        result = handler(message["payload"], message)
        if isinstance(result, SerializedMutationError):
            payload = serialize_serialized_mutation_error(result)
            return serialize_bridge_message_envelope(
                payload, event=event, request_id=message["requestId"]
            )
        if isinstance(result, dict) and result.get("ok") is False and "failure" in result:
            return make_bridge_error_response(
                event, result["failure"], {k: v for k, v in result.items() if k not in {"ok", "failure"}}, request_id=message["requestId"]
            )
        if isinstance(result, dict):
            return make_bridge_success_response(
                event, result, request_id=message["requestId"]
            )
        return make_bridge_success_response(
            event, {"value": result}, request_id=message["requestId"]
        )
    except SerializedMutationError as error:
        return serialize_bridge_message_envelope(
            serialize_serialized_mutation_error(error),
            event=event,
            request_id=message["requestId"],
        )
    except Exception as error:
        failure = {
            "error_type": type(error).__name__,
            "error_message": str(error),
        }
        return make_bridge_error_response(
            event,
            failure,
            {"value": None},
            request_id=message["requestId"],
        )


def handleBridgeCall(message: Any, call_handlers: dict[str, Callable[[Any, Any], Any]]) -> dict[str, Any]:
    return handle_bridge_call(message, call_handlers)


def handle_bridge_notification(
    message: Any,
    handler: Callable[[Any, Any], Any],
    *,
    event: str,
    normalizer: Callable[[Any], dict[str, Any]] | None = None,
) -> None:
    if not isinstance(message, dict):
        raise TypeError("message must be a dict")
    if message.get("type") != "notification":
        raise ValueError("Bridge message must have type='notification'")
    if message.get("event") != event:
        raise ValueError(f"Bridge notification must have event='{event}'")
    if not isinstance(message.get("payload"), dict):
        raise TypeError("Bridge notification payload must be a dict")

    payload = message["payload"]
    if normalizer is not None:
        payload = normalizer(payload)
    handler(payload, message)
    return None


def handleBridgeNotification(
    message: Any,
    handler: Callable[[Any, Any], Any],
    *,
    event: str,
    normalizer: Callable[[Any], dict[str, Any]] | None = None,
) -> None:
    return handle_bridge_notification(message, handler, event=event, normalizer=normalizer)


def make_clear_errors_and_warnings_bridge_handler(handler: Callable[[Any, Any], Any]):
    def _handler(payload: Any, message: Any):
        normalized = normalize_clear_errors_and_warnings_bridge_payload(payload)
        return handler(normalized, message)

    return _handler


def makeClearErrorsAndWarningsBridgeHandler(handler: Callable[[Any, Any], Any]):
    return make_clear_errors_and_warnings_bridge_handler(handler)


def make_inspect_element_bridge_handler(inspector: Callable[[Any, Any, Any, Any], Any]):
    def _handler(payload: Any, message: Any):
        normalized = normalize_inspect_element_bridge_payload(
            payload, request_id=message.get("requestId", message.get("requestID"))
        )
        result = inspector(
            normalized["requestID"],
            normalized["id"],
            normalized["path"],
            normalized["forceFullData"],
        )
        if not isinstance(result, dict):
            result = {"value": result}
        result = {
            "responseID": normalized["requestID"],
            "id": normalized["id"],
            "path": normalized["path"],
            "type": result.get("type", "full-data"),
            "value": result.get("value"),
            **{key: value for key, value in result.items() if key not in {"responseID", "id", "path", "type", "value"}},
        }
        return result

    return _handler


def makeInspectElementBridgeHandler(inspector: Callable[[Any, Any, Any, Any], Any]):
    return make_inspect_element_bridge_handler(inspector)


def handle_inspect_element_bridge_call(
    message: Any,
    inspector: Callable[[Any, Any, Any, Any], Any],
) -> dict[str, Any]:
    if not isinstance(message, dict):
        raise TypeError("message must be a dict")
    if message.get("event") != "inspectElement":
        raise ValueError("Bridge request event must be 'inspectElement'")
    normalized = normalize_inspect_element_bridge_payload(
        message.get("payload", {}), request_id=message.get("requestId")
    )
    try:
        result = inspector(
            normalized["requestID"],
            normalized["id"],
            normalized["path"],
            normalized["forceFullData"],
        )
        if not isinstance(result, dict):
            result = {"value": result}
        payload = {
            "responseID": normalized["requestID"],
            "id": normalized["id"],
            "path": normalized["path"],
            "type": result.get("type", "full-data"),
            "value": result.get("value"),
            **{key: value for key, value in result.items() if key not in {"responseID", "id", "path", "type", "value"}},
        }
        return make_bridge_success_response(
            "inspectedElement", payload, request_id=message.get("requestId")
        )
    except SerializedMutationError as error:
        return serialize_bridge_message_envelope(
            serialize_serialized_mutation_error(error),
            event="inspectedElement",
            request_id=message.get("requestId"),
        )
    except Exception as error:
        failure = {
            "error_type": type(error).__name__,
            "error_message": str(error),
        }
        return make_bridge_error_response(
            "inspectedElement",
            failure,
            {"responseID": message.get("requestId"), "value": None},
            request_id=message.get("requestId"),
        )


def handleInspectElementBridgeCall(
    message: Any,
    inspector: Callable[[Any, Any, Any, Any], Any],
) -> dict[str, Any]:
    return handle_inspect_element_bridge_call(message, inspector)


def make_inspect_screen_bridge_handler(inspector: Callable[[Any, Any, Any, Any], Any]):
    def _handler(payload: Any, message: Any):
        normalized = normalize_inspect_screen_bridge_payload(
            payload, request_id=message.get("requestId", message.get("requestID"))
        )
        result = inspector(
            normalized["requestID"],
            normalized["id"],
            normalized["path"],
            normalized["forceFullData"],
        )
        if not isinstance(result, dict):
            result = {"value": result}
        result = {
            "responseID": normalized["requestID"],
            "id": normalized["id"],
            "path": normalized["path"],
            "type": result.get("type", "full-data"),
            "value": result.get("value"),
            **{key: value for key, value in result.items() if key not in {"responseID", "id", "path", "type", "value"}},
        }
        return result

    return _handler


def makeInspectScreenBridgeHandler(inspector: Callable[[Any, Any, Any, Any], Any]):
    return make_inspect_screen_bridge_handler(inspector)


def handle_inspect_screen_bridge_call(
    message: Any,
    inspector: Callable[[Any, Any, Any, Any], Any],
) -> dict[str, Any]:
    if not isinstance(message, dict):
        raise TypeError("message must be a dict")
    if message.get("event") != "inspectScreen":
        raise ValueError("Bridge request event must be 'inspectScreen'")
    normalized = normalize_inspect_screen_bridge_payload(
        message.get("payload", {}), request_id=message.get("requestId")
    )
    try:
        result = inspector(
            normalized["requestID"],
            normalized["id"],
            normalized["path"],
            normalized["forceFullData"],
        )
        if not isinstance(result, dict):
            result = {"value": result}
        payload = {
            "responseID": normalized["requestID"],
            "id": normalized["id"],
            "path": normalized["path"],
            "type": result.get("type", "full-data"),
            "value": result.get("value"),
            **{key: value for key, value in result.items() if key not in {"responseID", "id", "path", "type", "value"}},
        }
        return make_bridge_success_response(
            "inspectedScreen", payload, request_id=message.get("requestId")
        )
    except Exception as error:
        failure = {
            "error_type": type(error).__name__,
            "error_message": str(error),
        }
        return make_bridge_error_response(
            "inspectedScreen",
            failure,
            {"responseID": message.get("requestId"), "value": None},
            request_id=message.get("requestId"),
        )


def handleInspectScreenBridgeCall(
    message: Any,
    inspector: Callable[[Any, Any, Any, Any], Any],
) -> dict[str, Any]:
    return handle_inspect_screen_bridge_call(message, inspector)


def handle_copy_element_path_bridge_notification(message: Any, handler: Callable[[Any, Any], Any]) -> None:
    return handle_bridge_notification(
        message,
        handler,
        event="copyElementPath",
        normalizer=normalize_copy_element_path_bridge_payload,
    )


def handleCopyElementPathBridgeNotification(message: Any, handler: Callable[[Any, Any], Any]) -> None:
    return handle_copy_element_path_bridge_notification(message, handler)


def handle_store_as_global_bridge_notification(message: Any, handler: Callable[[Any, Any], Any]) -> None:
    return handle_bridge_notification(
        message,
        handler,
        event="storeAsGlobal",
        normalizer=normalize_store_as_global_bridge_payload,
    )


def handleStoreAsGlobalBridgeNotification(message: Any, handler: Callable[[Any, Any], Any]) -> None:
    return handle_store_as_global_bridge_notification(message, handler)


def handle_override_suspense_milestone_bridge_notification(message: Any, handler: Callable[[Any, Any], Any]) -> None:
    return handle_bridge_notification(
        message,
        handler,
        event="overrideSuspenseMilestone",
        normalizer=normalize_override_suspense_milestone_bridge_payload,
    )


def handleOverrideSuspenseMilestoneBridgeNotification(message: Any, handler: Callable[[Any, Any], Any]) -> None:
    return handle_override_suspense_milestone_bridge_notification(message, handler)


def make_override_suspense_milestone_bridge_handler(handler: Callable[[Any, Any], Any]):
    def _handler(payload: Any, message: Any):
        normalized = normalize_override_suspense_milestone_bridge_payload(payload)
        return handler(normalized, message)

    return _handler


def makeOverrideSuspenseMilestoneBridgeHandler(handler: Callable[[Any, Any], Any]):
    return make_override_suspense_milestone_bridge_handler(handler)


def make_serialized_mutation_bridge_handler_from_target(target: Any | Callable[[], Any]):
    return make_serialized_mutation_bridge_handler(target)


def handle_serialized_mutation_bridge_call(
    message: Any,
    target: Any | Callable[[], Any],
) -> dict[str, Any]:
    if not isinstance(message, dict):
        raise TypeError("message must be a dict")
    normalized = normalize_serialized_mutation_bridge_payload(message.get("payload", {}))
    handler = make_serialized_mutation_bridge_handler(target)
    try:
        result = handler(normalized, message)
        return make_bridge_success_response(
            message.get("event", "serializedMutation"), result, request_id=message.get("requestId")
        )
    except SerializedMutationError as error:
        return serialize_bridge_message_envelope(
            serialize_serialized_mutation_error(error),
            event=message.get("event", "serializedMutation"),
            request_id=message.get("requestId"),
        )
    except Exception as error:
        failure = {
            "error_type": type(error).__name__,
            "error_message": str(error),
        }
        return make_bridge_error_response(
            message.get("event", "serializedMutation"),
            failure,
            {"value": None},
            request_id=message.get("requestId"),
        )


def handleSerializedMutationBridgeCall(
    message: Any,
    target: Any | Callable[[], Any],
) -> dict[str, Any]:
    return handle_serialized_mutation_bridge_call(message, target)


def dispatch_bridge_message(
    message: Any,
    *,
    call_handlers: dict[str, Callable[[Any, Any], Any]] | None = None,
    notification_handlers: dict[str, Callable[[Any, Any], Any]] | None = None,
) -> Any:
    if not isinstance(message, dict):
        raise TypeError("message must be a dict")
    message_type = message.get("type")
    if message_type == "request":
        return handle_bridge_call(message, call_handlers or {})
    if message_type == "notification":
        handlers = notification_handlers or {}
        handler = handlers.get(message.get("event"))
        if handler is None:
            return None
        return handle_bridge_notification(
            message,
            handler,
            event=message.get("event"),
            normalizer=lambda payload: payload,
        )
    raise ValueError("Bridge message must be a 'request' or 'notification'")


def dispatchBridgeMessage(
    message: Any,
    *,
    call_handlers: dict[str, Callable[[Any, Any], Any]] | None = None,
    notification_handlers: dict[str, Callable[[Any, Any], Any]] | None = None,
) -> Any:
    return dispatch_bridge_message(
        message,
        call_handlers=call_handlers,
        notification_handlers=notification_handlers,
    )


def make_devtools_backend_notification_handlers(
    *,
    clear_errors_and_warnings: Callable[[Any, Any], Any] | None = None,
    clear_errors_for_element: Callable[[Any, Any], Any] | None = None,
    clear_warnings_for_element: Callable[[Any, Any], Any] | None = None,
    copy_element_path: Callable[[Any, Any], Any] | None = None,
    store_as_global: Callable[[Any, Any], Any] | None = None,
    override_suspense_milestone: Callable[[Any, Any], Any] | None = None,
) -> dict[str, Callable[[Any, Any], Any]]:
    handlers: dict[str, Callable[[Any, Any], Any]] = {}
    if clear_errors_and_warnings is not None:
        handlers["clearErrorsAndWarnings"] = make_clear_errors_and_warnings_bridge_handler(
            clear_errors_and_warnings
        )
    if clear_errors_for_element is not None:
        handlers["clearErrorsForElementID"] = lambda payload, message: clear_errors_for_element(
            normalize_clear_errors_for_element_bridge_payload(payload), message
        )
    if clear_warnings_for_element is not None:
        handlers["clearWarningsForElementID"] = lambda payload, message: clear_warnings_for_element(
            normalize_clear_errors_for_element_bridge_payload(payload), message
        )
    if copy_element_path is not None:
        handlers["copyElementPath"] = lambda payload, message: copy_element_path(
            normalize_copy_element_path_bridge_payload(payload), message
        )
    if store_as_global is not None:
        handlers["storeAsGlobal"] = lambda payload, message: store_as_global(
            normalize_store_as_global_bridge_payload(payload), message
        )
    if override_suspense_milestone is not None:
        handlers["overrideSuspenseMilestone"] = make_override_suspense_milestone_bridge_handler(
            override_suspense_milestone
        )
    return handlers


def makeDevtoolsBackendNotificationHandlers(**kwargs) -> dict[str, Callable[[Any, Any], Any]]:
    return make_devtools_backend_notification_handlers(**kwargs)
