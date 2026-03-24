from __future__ import annotations

import copy
from dataclasses import dataclass

META_KEY = "__meta__"
INSPECTED_KEY = "__inspected__"
UNSERIALIZABLE_KEY = "__unserializable__"
DEVTOOLS_UNDEFINED = object()


class HydratedDict(dict):
    pass


class HydratedList(list):
    pass


@dataclass
class SerializedMutationError(Exception):
    index: int
    operation: dict
    cause: Exception
    partial_result: dict

    def __str__(self) -> str:
        return f"Serialized mutation failed at index {self.index}: {self.cause}"


def _legacy_metadata(value):
    if isinstance(value, dict) and META_KEY in value:
        return value[META_KEY]
    return None


def has_metadata(value):
    return hasattr(value, "_meta") or _legacy_metadata(value) is not None


def get_metadata(value):
    if hasattr(value, "_meta"):
        return value._meta
    return _legacy_metadata(value)


def _copy_metadata(source, target):
    metadata = get_metadata(source)
    if metadata is not None:
        set_metadata(target, dict(metadata))
    if is_inspected(source):
        mark_inspected(target, True)
    if is_unserializable(source):
        mark_unserializable(target, True)
    return target


def copy_with_metadata(value, metadata=None):
    if isinstance(value, HydratedList):
        cloned = HydratedList(copy.deepcopy(list(value)))
        _copy_metadata(value, cloned)
    elif isinstance(value, HydratedDict):
        cloned = HydratedDict(copy.deepcopy(dict(value)))
        _copy_metadata(value, cloned)
    elif isinstance(value, list):
        cloned = HydratedList(copy.deepcopy(value))
    elif isinstance(value, dict):
        cloned = HydratedDict(copy.deepcopy(dict(value)))
        legacy = get_metadata(value)
        if legacy is not None:
            set_metadata(cloned, dict(legacy))
        if value.get(INSPECTED_KEY):
            mark_inspected(cloned, True)
        if value.get(UNSERIALIZABLE_KEY):
            mark_unserializable(cloned, True)
    else:
        cloned = copy.deepcopy(value)
    if metadata is not None and isinstance(cloned, (HydratedDict, HydratedList)):
        set_metadata(cloned, metadata)
    return cloned


def set_metadata(value, metadata):
    if isinstance(value, (HydratedDict, HydratedList)):
        value._meta = dict(metadata)
        return value
    if isinstance(value, dict):
        value[META_KEY] = dict(metadata)
        return value
    return value


def mark_inspected(value, state: bool = True):
    if isinstance(value, (HydratedDict, HydratedList)):
        meta = dict(get_metadata(value) or {})
        meta[INSPECTED_KEY] = state
        value._meta = meta
    elif isinstance(value, dict):
        value[INSPECTED_KEY] = state
    return value


def mark_unserializable(value, state: bool = True):
    if isinstance(value, (HydratedDict, HydratedList)):
        meta = dict(get_metadata(value) or {})
        meta[UNSERIALIZABLE_KEY] = state
        value._meta = meta
    elif isinstance(value, dict):
        value[UNSERIALIZABLE_KEY] = state
    return value


def is_inspected(value):
    if isinstance(value, (HydratedDict, HydratedList)):
        return bool((get_metadata(value) or {}).get(INSPECTED_KEY, False))
    if isinstance(value, dict):
        return bool(value.get(INSPECTED_KEY, False))
    return False


def is_unserializable(value):
    if isinstance(value, (HydratedDict, HydratedList)):
        return bool((get_metadata(value) or {}).get(UNSERIALIZABLE_KEY, False))
    if isinstance(value, dict):
        return bool(value.get(UNSERIALIZABLE_KEY, False))
    return False


def replace_metadata_value(value, replacement):
    replaced = copy_with_metadata(replacement)
    return _copy_metadata(value, replaced)


def _iter_transport_paths(items):
    if isinstance(items, list):
        return {tuple(item) for item in items}
    return set()


def _wrapped_from_meta_payload(data: dict):
    wrapper = HydratedList() if all(isinstance(key, int) for key in data if not isinstance(key, str) or key.isdigit()) and data.get("type") in {"iterator", "typed_array", "html_all_collection", "array"} else HydratedDict()
    _metadata = {k: v for k, v in data.items() if isinstance(k, str) and not isinstance(wrapper, HydratedList) and k not in {META_KEY, INSPECTED_KEY, UNSERIALIZABLE_KEY}}
    if isinstance(wrapper, HydratedList):
        numeric_keys = sorted(k for k in data if isinstance(k, int))
        for key in numeric_keys:
            wrapper.append(data[key])
    else:
        for key, value in data.items():
            if key in {"type", "name", "preview_short", "preview_long", "inspectable", "readonly", "size"}:
                continue
            wrapper[key] = value
    meta = {k: data[k] for k in ("type", "name", "preview_short", "preview_long", "inspectable", "readonly", "size") if k in data}
    set_metadata(wrapper, meta)
    return wrapper


def hydrate_helper(payload, path=None):
    path = path or []
    if not isinstance(payload, dict):
        return payload
    data = payload.get("data", payload)
    cleaned = _iter_transport_paths(payload.get("cleaned", []))
    unserializable = _iter_transport_paths(payload.get("unserializable", []))

    def hydrate_value(value, current_path):
        if tuple(current_path) in cleaned:
            if value.get("type") == "infinity":
                return float("inf")
            if value.get("type") == "nan":
                return float("nan")
            if value.get("type") == "undefined":
                return DEVTOOLS_UNDEFINED
            wrapped = _wrapped_from_meta_payload(value) if isinstance(value, dict) else value
            if tuple(current_path) in unserializable:
                mark_unserializable(wrapped, True)
            if path and tuple(current_path) == tuple(path):
                mark_inspected(wrapped, True)
            return wrapped
        if isinstance(value, dict):
            if value.get("unserializable") is True or value.get("type") in {
                "react_element",
                "error",
                "class_instance",
                "iterator",
                "array",
                "typed_array",
                "array_buffer",
                "data_view",
                "thenable",
                "react_lazy",
                "html_element",
                "html_all_collection",
                "bigint",
                "unknown",
                "date",
                "regexp",
                "symbol",
                "object",
            }:
                wrapped = _wrapped_from_meta_payload(value)
                if isinstance(wrapped, HydratedList):
                    for index, child_value in enumerate(list(wrapped)):
                        wrapped[index] = hydrate_value(child_value, current_path + [index])
                else:
                    for key in list(wrapped.keys()):
                        wrapped[key] = hydrate_value(wrapped[key], current_path + [key])
                if tuple(current_path) in unserializable:
                    mark_unserializable(wrapped, True)
                if tuple(current_path) == tuple(path):
                    mark_inspected(wrapped, True)
                return wrapped
            wrapped = HydratedDict()
            for key, child in value.items():
                wrapped[key] = hydrate_value(child, current_path + [key])
            if tuple(current_path) in unserializable:
                mark_unserializable(wrapped, True)
            if tuple(current_path) == tuple(path):
                mark_inspected(wrapped, True)
            return wrapped
        if isinstance(value, list):
            wrapped = HydratedList(hydrate_value(item, current_path + [index]) for index, item in enumerate(value))
            if tuple(current_path) in unserializable:
                mark_unserializable(wrapped, True)
            if tuple(current_path) == tuple(path):
                mark_inspected(wrapped, True)
            return wrapped
        return value

    return hydrate_value(data, path or [])


def get_in_object(value, path):
    current = value
    for part in path:
        current = current[part]
    return current


def _container_and_key(value, path):
    if not path:
        return None, None
    current = value
    for part in path[:-1]:
        current = current[part]
    return current, path[-1]


def set_in_object(value, path, replacement):
    if not path:
        return replacement
    current, key = _container_and_key(value, path)
    current[key] = replacement
    return value


def delete_in_path(value, path):
    current = copy_with_metadata(value)
    container, key = _container_and_key(current, path)
    if isinstance(container, list):
        del container[key]
    else:
        del container[key]
    return current


def delete_path_in_object(value, path):
    mutated = delete_in_path(value, path)
    if path == []:
        return mutated
    container, key = _container_and_key(value, path)
    if isinstance(container, list):
        del container[key]
    else:
        del container[key]
    return value


def rename_in_path(value, path, new_path):
    current = copy_with_metadata(value)
    moved = get_in_object(current, path)
    current = delete_in_path(current, path)
    return set_in_object(current, new_path, moved)


def rename_path_in_object(value, path, new_path):
    if path == new_path:
        return value
    moved = get_in_object(value, path)
    delete_path_in_object(value, path)
    return set_in_object(value, new_path, moved)


def replace_in_path(value, replacement, path):
    if not path:
        return _copy_metadata(value, copy_with_metadata(replacement))
    current = copy_with_metadata(value)
    original = get_in_object(current, path)
    replaced = _copy_metadata(original, copy_with_metadata(replacement))
    return set_in_object(current, path, replaced)


def update_in_path(value, path, updater):
    current = copy_with_metadata(value)
    if not path:
        return _copy_metadata(current, copy_with_metadata(updater(current)))
    original = get_in_object(current, path)
    updated = _copy_metadata(original, copy_with_metadata(updater(copy_with_metadata(original))))
    return set_in_object(current, path, updated)


def mutate_in_path(value, path, mutator):
    current = copy_with_metadata(value)
    target = current if not path else get_in_object(current, path)
    mutator(target)
    return current


def fill_in_path(value, filler, path):
    current = copy_with_metadata(value)
    if not path:
        return filler
    container, key = _container_and_key(current, path)
    if isinstance(container, list) and isinstance(key, int):
        while len(container) <= key:
            container.append(None)
        container[key] = filler
    else:
        container[key] = filler
    return current


def apply_serialized_mutation(value, operation):
    op = operation.get("op")
    if not op:
        raise ValueError("Serialized mutation must include an 'op'")
    if op == "delete" and not operation.get("path"):
        raise ValueError("delete operations require a non-empty path")
    if op == "set":
        return set_in_object(copy_with_metadata(value), operation["path"], operation["value"])
    if op == "delete":
        return delete_in_path(value, operation["path"])
    if op == "rename":
        return rename_in_path(value, operation["oldPath"], operation["newPath"])
    if op == "replace":
        return replace_in_path(value, operation["value"], operation["path"])
    if op == "update":
        updater = operation.get("updater")
        if not callable(updater):
            raise TypeError("update operation requires callable 'updater'")
        return update_in_path(value, operation["path"], updater)
    if op == "mutate":
        mutator = operation.get("mutator")
        if not callable(mutator):
            raise TypeError("mutate operation requires callable 'mutator'")
        return mutate_in_path(value, operation["path"], mutator)
    raise ValueError("Unsupported serialized mutation op")


def apply_serialized_mutations(value, operations, mode="fail-fast", rollback=False):
    if mode not in {"fail-fast", "best-effort"}:
        raise ValueError("Batch mutation mode")
    if not isinstance(rollback, bool):
        raise TypeError("rollback flag")
    working = copy_with_metadata(value)
    original = copy_with_metadata(value)
    errors = []
    applied_indices = []
    failed_indices = []
    for index, operation in enumerate(operations):
        try:
            working = apply_serialized_mutation(working, operation)
            applied_indices.append(index)
        except Exception as error:  # noqa: BLE001
            failed_indices.append(index)
            errors.append(
                {
                    "index": index,
                    "operation": operation,
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                }
            )
            partial = {
                "mode": mode,
                "applied": len(applied_indices),
                "applied_indices": applied_indices,
                "failed_indices": failed_indices,
                "rolled_back": rollback,
                "value": original if rollback else working,
                "errors": errors,
            }
            if mode == "fail-fast":
                raise SerializedMutationError(index, operation, error, partial) from error
    return {
        "mode": mode,
        "applied": len(applied_indices),
        "applied_indices": applied_indices,
        "failed_indices": failed_indices,
        "rolled_back": rollback and bool(errors),
        "value": original if rollback and errors else working,
        "errors": errors,
    }


def serialize_serialized_mutation_result(result):
    return {
        "ok": True,
        "failure": None,
        **{k: (copy_with_metadata(v) if k == "value" else v) for k, v in result.items()},
    }


def serialize_serialized_mutation_error(error):
    return {
        "ok": False,
        **dict(error.partial_result.items()),
        "failure": {
            "index": error.index,
            "operation": error.operation,
            "error_type": type(error.cause).__name__,
            "error_message": str(error.cause),
        },
    }


def serialize_serialized_mutation_outcome(outcome):
    return serialize_serialized_mutation_error(outcome) if isinstance(outcome, SerializedMutationError) else serialize_serialized_mutation_result(outcome)


def serialize_bridge_message_envelope(payload, *, event, message_type="response", request_id=None):
    if not event:
        raise ValueError("event")
    if not message_type:
        raise ValueError("type")
    envelope = {"event": event, "type": message_type, "payload": copy.deepcopy(payload)}
    if request_id is not None:
        envelope["requestId"] = request_id
    return envelope


_request_counter = 0


def _next_request_id():
    global _request_counter
    _request_counter += 1
    return _request_counter


def make_bridge_request(event, payload, request_id=None):
    if request_id is not None and not isinstance(request_id, (int, str)):
        raise TypeError("request id")
    return {"event": event, "type": "request", "payload": payload, "requestId": _next_request_id() if request_id is None else request_id}


def make_bridge_response(event, payload, request_id=None):
    return {"event": event, "type": "response", "payload": payload, "requestId": _next_request_id() if request_id is None else request_id}


def make_bridge_success_response(event, payload, request_id=None):
    return make_bridge_response(event, {"ok": True, "failure": None, **payload}, request_id)


def make_bridge_error_response(event, failure, payload, request_id=None):
    return make_bridge_response(event, {"ok": False, "failure": failure, **payload}, request_id)


def make_bridge_notification(event, payload):
    return {"event": event, "type": "notification", "payload": payload}


def make_bridge_call(event, payload, request_id=None):
    return make_bridge_request(event, payload, request_id)


def serialize_serialized_mutation_message(outcome, *, event, request_id):
    payload = serialize_serialized_mutation_outcome(outcome)
    return serialize_bridge_message_envelope(payload, event=event, message_type="response", request_id=request_id)


def dispatch_bridge_message(message, *, call_handlers=None, notification_handlers=None):
    if message.get("type") not in {"request", "notification"}:
        raise ValueError("request' or 'notification")
    if message["type"] == "request":
        return handle_bridge_call(message, call_handlers or {})
    return handle_bridge_notification(message, notification_handlers or {})


def handle_bridge_call(message, handlers):
    if not isinstance(message, dict):
        raise TypeError("dict")
    if message.get("type") != "request":
        raise ValueError("type='request'")
    if "event" not in message:
        raise ValueError("event")
    if "requestId" not in message:
        raise ValueError("requestId")
    if not isinstance(message.get("payload"), dict):
        raise TypeError("payload")
    if not isinstance(message.get("requestId"), (int, str)):
        raise TypeError("request id")
    handler = handlers.get(message["event"])
    if handler is None:
        return make_bridge_response(message["event"], {"ok": False, "failure": {"error_type": "LookupError"}}, message["requestId"])
    try:
        result = handler(message["payload"], message)
        payload = result if isinstance(result, dict) and "ok" in result else {"ok": True, "failure": None, **result}
        return make_bridge_response(message["event"], payload, message["requestId"])
    except SerializedMutationError as error:
        return make_bridge_response(message["event"], serialize_serialized_mutation_error(error), message["requestId"])
    except Exception as error:  # noqa: BLE001
        return make_bridge_response(message["event"], {"ok": False, "failure": {"error_type": type(error).__name__, "error_message": str(error)}}, message["requestId"])


def handle_bridge_notification(message, handlers=None, event=None, normalizer=None):
    if not isinstance(message, dict):
        raise TypeError("dict")
    if message.get("type") != "notification":
        raise ValueError("type='notification'")
    handlers = handlers or {}
    payload = message["payload"]
    if normalizer is not None:
        payload = normalizer(payload)
    handler = handlers.get(message["event"]) if isinstance(handlers, dict) else handlers
    if callable(handler):
        return handler(payload, message)
    return None


def normalize_serialized_mutation_bridge_payload(payload):
    if not isinstance(payload, dict):
        raise TypeError("dict")
    if "mode" in payload and not isinstance(payload["mode"], str):
        raise TypeError("'mode' must be a string")
    if "rollback" in payload and not isinstance(payload["rollback"], bool):
        raise TypeError("'rollback' must be a bool")
    operations = payload.get("operations")
    if not isinstance(operations, list):
        raise TypeError("'operations' must be a list")
    if any(not isinstance(item, dict) for item in operations):
        raise TypeError("dict items")
    return {"operations": operations, "mode": payload.get("mode", "fail-fast"), "rollback": payload.get("rollback", False)}


def normalize_inspect_element_bridge_payload(payload, request_id=None):
    if not isinstance(payload, dict):
        raise TypeError("dict")
    if "id" not in payload:
        raise ValueError("include 'id'")
    if "path" in payload and payload["path"] is not None and not isinstance(payload["path"], list):
        raise TypeError("'path' must be a list or None")
    if "forceFullData" in payload and not isinstance(payload["forceFullData"], bool):
        raise TypeError("'forceFullData' must be a bool")
    return {"id": payload["id"], "path": payload.get("path"), "forceFullData": payload.get("forceFullData", False), "rendererID": payload.get("rendererID"), "requestID": request_id}


def normalize_inspect_screen_bridge_payload(payload, request_id=None):
    if not isinstance(payload, dict):
        raise TypeError("dict")
    if "id" not in payload:
        raise ValueError("include 'id'")
    return {"id": payload["id"], "path": payload.get("path"), "forceFullData": payload.get("forceFullData", False), "rendererID": payload.get("rendererID"), "requestID": request_id}


def normalize_clear_errors_and_warnings_bridge_payload(payload):
    return {"rendererID": payload["rendererID"]}


def normalize_clear_errors_for_element_bridge_payload(payload):
    if "rendererID" not in payload:
        raise ValueError("rendererID")
    return payload


def normalize_copy_element_path_bridge_payload(payload):
    if not isinstance(payload.get("path"), list):
        raise TypeError("'path' must be a list")
    return payload


def normalize_store_as_global_bridge_payload(payload):
    if "count" in payload and not isinstance(payload["count"], int):
        raise TypeError("count")
    return payload


def normalize_override_suspense_milestone_bridge_payload(payload):
    if not isinstance(payload.get("suspendedSet"), list):
        raise TypeError("'suspendedSet' must be a list")
    return payload


def make_serialized_mutation_bridge_handler(target_or_factory):
    return lambda payload, _message: apply_serialized_mutations(target_or_factory() if callable(target_or_factory) else target_or_factory, payload["operations"], mode=payload.get("mode", "fail-fast"), rollback=payload.get("rollback", False))


def handle_serialized_mutation_bridge_call(message, target_or_factory):
    payload = normalize_serialized_mutation_bridge_payload(message["payload"])
    return handle_bridge_call({"type": "request", "event": message["event"], "payload": payload, "requestId": message["requestId"]}, {message["event"]: make_serialized_mutation_bridge_handler(target_or_factory)})


def make_inspect_element_bridge_handler(inspector):
    def handler(payload, raw_message):
        result = inspector(raw_message["requestId"], payload["id"], payload.get("path"), payload.get("forceFullData", False))
        if isinstance(result, dict):
            result.setdefault("id", payload["id"])
            result.setdefault("responseID", raw_message["requestId"])
        return result
    return handler


def handle_inspect_element_bridge_call(message, inspector):
    if message["event"] != "inspectElement":
        raise ValueError("event must be 'inspectElement'")
    payload = normalize_inspect_element_bridge_payload(message["payload"], request_id=message["requestId"])
    try:
        result = inspector(message["requestId"], payload["id"], payload.get("path"), payload.get("forceFullData", False))
        if isinstance(result, dict):
            result.setdefault("id", payload["id"])
            result.setdefault("responseID", message["requestId"])
        return serialize_bridge_message_envelope({"ok": True, "failure": None, **result}, event="inspectedElement", message_type="response", request_id=message["requestId"])
    except Exception as error:  # noqa: BLE001
        return serialize_bridge_message_envelope(
            {"ok": False, "failure": {"error_type": type(error).__name__, "error_message": str(error)}},
            event="inspectedElement",
            message_type="response",
            request_id=message["requestId"],
        )


def make_inspect_screen_bridge_handler(inspector):
    def handler(payload, raw_message):
        result = inspector(raw_message["requestId"], payload["id"], payload.get("path"), payload.get("forceFullData", False))
        if isinstance(result, dict):
            result.setdefault("id", payload["id"])
            result.setdefault("responseID", raw_message["requestId"])
        return result
    return handler


def handle_inspect_screen_bridge_call(message, inspector):
    payload = normalize_inspect_screen_bridge_payload(message["payload"], request_id=message["requestId"])
    try:
        result = inspector(message["requestId"], payload["id"], payload.get("path"), payload.get("forceFullData", False))
        if isinstance(result, dict):
            result.setdefault("id", payload["id"])
            result.setdefault("responseID", message["requestId"])
        return serialize_bridge_message_envelope({"ok": True, "failure": None, **result}, event="inspectedScreen", message_type="response", request_id=message["requestId"])
    except Exception as error:  # noqa: BLE001
        return serialize_bridge_message_envelope(
            {"ok": False, "failure": {"error_type": type(error).__name__, "error_message": str(error)}},
            event="inspectedScreen",
            message_type="response",
            request_id=message["requestId"],
        )


def make_clear_errors_and_warnings_bridge_handler(handler):
    return lambda payload, message: handler(normalize_clear_errors_and_warnings_bridge_payload(payload), message)


def handle_copy_element_path_bridge_notification(message, handler):
    return handler(normalize_copy_element_path_bridge_payload(message["payload"]), message)


def handle_store_as_global_bridge_notification(message, handler):
    return handler(normalize_store_as_global_bridge_payload(message["payload"]), message)


def make_override_suspense_milestone_bridge_handler(handler):
    return lambda payload, message: handler(normalize_override_suspense_milestone_bridge_payload(payload), message)


def handle_override_suspense_milestone_bridge_notification(message, handler):
    return handler(normalize_override_suspense_milestone_bridge_payload(message["payload"]), message)


def make_devtools_backend_notification_handlers(**handlers):
    def noop(payload, message):  # noqa: ARG001
        return None

    return {
        "clearErrorsAndWarnings": make_clear_errors_and_warnings_bridge_handler(handlers.get("clear_errors_and_warnings", noop)),
        "clearErrorsForElementID": lambda payload, message: handlers.get("clear_errors_for_element", noop)(normalize_clear_errors_for_element_bridge_payload(payload), message),
        "clearWarningsForElementID": lambda payload, message: handlers.get("clear_warnings_for_element", noop)(normalize_clear_errors_for_element_bridge_payload(payload), message),
        "copyElementPath": lambda payload, message: handlers.get("copy_element_path", noop)(normalize_copy_element_path_bridge_payload(payload), message),
        "storeAsGlobal": lambda payload, message: handlers.get("store_as_global", noop)(normalize_store_as_global_bridge_payload(payload), message),
        "overrideSuspenseMilestone": lambda payload, message: handlers.get("override_suspense_milestone", noop)(normalize_override_suspense_milestone_bridge_payload(payload), message),
    }


def _camel(name):
    parts = name.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


for _name in list(globals()):
    if _name.startswith(("make_", "handle_", "normalize_", "serialize_", "apply_", "copy_", "delete_", "dispatch_", "fill_", "get_", "has_", "is_", "mark_", "mutate_", "rename_", "replace_", "set_", "update_")):
        globals()[_camel(_name)] = globals()[_name]

copyWithMetadata = copy_with_metadata
deletePathInObject = delete_path_in_object
renamePathInObject = rename_path_in_object
replaceMetadataValue = replace_metadata_value
serializeBridgeMessageEnvelope = serialize_bridge_message_envelope
