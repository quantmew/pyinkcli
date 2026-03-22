"""DevTools inspection helpers aligned with reconciler-facing inspection responsibilities."""

from __future__ import annotations

import array as array_module
import asyncio
import concurrent.futures
import datetime as datetime_module
import enum
import json
import re
import traceback
from collections import abc as collections_abc
from typing import TYPE_CHECKING, Any

from pyinkcli._component_runtime import isElement
from pyinkcli.packages.react_reconciler.ReactFiberReconciler import packageInfo

if TYPE_CHECKING:
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler


def inspectDevtoolsElement(
    reconciler: _Reconciler,
    request_id: int,
    node_id: str,
    inspected_paths: Any | None = None,
    force_full_data: bool = False,
) -> dict[str, Any]:
    path: list[Any] | None = None
    if isinstance(inspected_paths, list):
        path = list(inspected_paths)

    if reconciler._is_most_recently_inspected(node_id) and not force_full_data:
        if path is not None:
            reconciler._merge_inspected_path(path)
        if not reconciler._devtools_has_element_updated_since_last_inspected:
            if path is not None:
                element = reconciler._devtools_inspected_elements.get(node_id)
                if element is None:
                    return {
                        "id": node_id,
                        "responseID": request_id,
                        "type": "not-found",
                    }
                value, found = getNestedValue(reconciler, element, path)
                root_key = path[0] if path else None
                if found and isinstance(root_key, str):
                    value = cleanDevtoolsValueForBridge(
                        reconciler,
                        value,
                        root_key=root_key,
                        path=path,
                    )
                return {
                    "id": node_id,
                    "responseID": request_id,
                    "type": "hydrated-path",
                    "path": path,
                    "value": value if found else None,
                }
            return {
                "id": node_id,
                "responseID": request_id,
                "type": "no-change",
            }
    else:
        reconciler._devtools_currently_inspected_paths = {}

    if path is not None:
        reconciler._merge_inspected_path(path)

    element = reconciler._devtools_inspected_elements.get(node_id)
    if element is None:
        return {
            "id": node_id,
            "responseID": request_id,
            "type": "not-found",
        }
    reconciler._devtools_most_recently_inspected_id = node_id
    reconciler._devtools_has_element_updated_since_last_inspected = False
    return {
        "id": node_id,
        "responseID": request_id,
        "type": "full-data",
        "value": cleanDevtoolsInspectedElementForBridge(reconciler, element),
    }


def getSerializedDevtoolsElementValueByPath(
    reconciler: _Reconciler,
    node_id: str,
    path: list[Any],
) -> str | None:
    element = reconciler._devtools_inspected_elements.get(node_id)
    if element is None:
        return None
    value, found = getNestedValue(reconciler, element, path)
    if not found:
        return None
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return repr(value)


def getDevtoolsElementValueByPath(
    reconciler: _Reconciler,
    node_id: str,
    path: list[Any],
) -> Any:
    element = reconciler._devtools_inspected_elements.get(node_id)
    if element is None:
        return None
    value, found = getNestedValue(reconciler, element, path)
    if not found:
        return None
    return cloneDevtoolsValue(reconciler, value)


def cloneDevtoolsValue(_reconciler: _Reconciler, value: Any) -> Any:
    if type(value) is dict:
        return {
            key: cloneDevtoolsValue(_reconciler, item)
            for key, item in value.items()
        }
    if isinstance(value, dict):
        try:
            return type(value)(
                (key, cloneDevtoolsValue(_reconciler, item))
                for key, item in value.items()
            )
        except Exception:
            return {
                key: cloneDevtoolsValue(_reconciler, item)
                for key, item in value.items()
            }
    if isinstance(value, list):
        return [cloneDevtoolsValue(_reconciler, item) for item in value]
    return value


def fingerprintDevtoolsValue(reconciler: _Reconciler, value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {
            str(key): fingerprintDevtoolsValue(reconciler, item)
            for key, item in sorted(value.items(), key=lambda entry: str(entry[0]))
        }
    if isinstance(value, list):
        return [fingerprintDevtoolsValue(reconciler, item) for item in value]
    if isElement(value):
        element_type = getattr(value, "type", None)
        if callable(element_type):
            display_name = reconciler._get_component_display_name(element_type)
        else:
            display_name = str(element_type)
        return {
            "__element__": display_name,
            "key": getattr(value, "key", None),
            "childrenCount": len(getattr(value, "children", ()) or ()),
        }
    if isinstance(value, BaseException):
        return {
            "__error__": type(value).__name__,
            "message": str(value),
        }
    if callable(value):
        return {"__callable__": getattr(value, "__name__", repr(value))}
    return repr(value)


def buildDevtoolsFingerprint(reconciler: _Reconciler, value: Any) -> str:
    return json.dumps(
        fingerprintDevtoolsValue(reconciler, value),
        ensure_ascii=False,
        sort_keys=True,
    )


def getDevtoolsDataType(_reconciler: _Reconciler, value: Any) -> str:
    if value is None:
        return "null"
    if getattr(value, "__ink_devtools_react_lazy__", False):
        return "react_lazy"
    if getattr(value, "__ink_devtools_html_element__", False):
        return "html_element"
    if getattr(value, "__ink_devtools_html_all_collection__", False):
        return "html_all_collection"
    if getattr(value, "__ink_devtools_bigint__", False):
        return "bigint"
    if getattr(value, "__ink_devtools_unknown__", False):
        return "unknown"
    if isinstance(value, enum.Enum):
        return "symbol"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "number"
    if isinstance(value, float):
        if value == float("inf") or value == float("-inf"):
            return "infinity"
        if value != value:
            return "nan"
        return "number"
    if isinstance(
        value,
        (
            datetime_module.date,
            datetime_module.datetime,
            datetime_module.time,
        ),
    ):
        return "date"
    if isinstance(value, re.Pattern):
        return "regexp"
    if isinstance(value, (bytes, bytearray)):
        return "array_buffer"
    if isinstance(value, memoryview):
        return "data_view"
    if isinstance(value, array_module.array):
        return "typed_array"
    if isinstance(value, (asyncio.Future, concurrent.futures.Future)):
        return "thenable"
    if hasattr(value, "then") and callable(value.then):
        return "thenable"
    if isinstance(value, collections_abc.Iterator):
        return "opaque_iterator"
    if isinstance(
        value,
        (
            set,
            frozenset,
            collections_abc.ItemsView,
            collections_abc.KeysView,
            collections_abc.ValuesView,
        ),
    ):
        return "iterator"
    if isinstance(value, collections_abc.Mapping) and type(value) is not dict:
        return "iterator"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isElement(value):
        return "react_element"
    if isinstance(value, BaseException):
        return "error"
    if callable(value):
        return "function"
    if hasattr(value, "__dict__"):
        return "class_instance"
    return "object"


def previewDevtoolsValue(
    reconciler: _Reconciler,
    value: Any,
    *,
    short: bool,
) -> str:
    data_type = getDevtoolsDataType(reconciler, value)
    if data_type == "react_lazy":
        payload = getattr(value, "_payload", None)
        status = getDevtoolsLazyStatus(reconciler, payload)
        if status == "fulfilled":
            resolved = getDevtoolsLazyResolvedValue(reconciler, payload)
            if short:
                return "fulfilled lazy() {…}"
            if resolved is not None:
                return f"fulfilled lazy() {{{previewDevtoolsValue(reconciler, resolved, short=True)}}}"
            return "fulfilled lazy() {…}"
        if status == "rejected":
            reason = getDevtoolsLazyRejectedValue(reconciler, payload)
            if short:
                return "rejected lazy() {…}"
            if reason is not None:
                return f"rejected lazy() {{{previewDevtoolsValue(reconciler, reason, short=True)}}}"
            return "rejected lazy() {…}"
        return "pending lazy()" if status == "pending" else "lazy()"
    if data_type == "html_element":
        tag_name = getattr(value, "tagName", "div")
        preview = f"<{str(tag_name).lower()} />"
        return preview if len(preview) <= 50 else preview[:50] + "..."
    if data_type == "bigint":
        preview = f"{getattr(value, 'value', value)}n"
        return preview if len(preview) <= 50 else preview[:50] + "..."
    if data_type == "unknown":
        preview = getattr(value, "__ink_devtools_unknown_preview__", "")
        if short:
            return "[Exception]"
        return f"[Exception: {preview}]" if preview else "[Exception]"
    if data_type == "string":
        preview = json.dumps(value, ensure_ascii=False)
        if len(preview) > 50:
            preview = preview[:50] + "..."
        return preview
    if data_type == "date":
        preview = str(value)
        return preview if len(preview) <= 50 else preview[:50] + "..."
    if data_type == "regexp":
        preview = repr(value)
        return preview if len(preview) <= 50 else preview[:50] + "..."
    if data_type == "symbol":
        preview = str(value)
        return preview if len(preview) <= 50 else preview[:50] + "..."
    if data_type == "html_all_collection":
        preview = str(value)
        return preview if len(preview) <= 50 else preview[:50] + "..."
    if data_type == "array_buffer":
        size = getDevtoolsBufferSize(reconciler, value)
        return f"ArrayBuffer({size})"
    if data_type == "data_view":
        size = getDevtoolsBufferSize(reconciler, value)
        return f"DataView({size})"
    if data_type == "object":
        if short:
            return "{…}"
        parts: list[str] = []
        for key, item in list(value.items())[:4]:
            parts.append(f"{key}: {previewDevtoolsValue(reconciler, item, short=True)}")
        preview = ", ".join(parts)
        if len(value) > 4:
            preview += ", ..."
        if len(preview) > 50:
            preview = preview[:50] + "..."
        return "{" + preview + "}"
    if data_type == "array":
        if short:
            return f"Array({len(value)})"
        preview = ", ".join(
            previewDevtoolsValue(reconciler, item, short=True)
            for item in value[:4]
        )
        if len(value) > 4:
            preview += ", ..."
        if len(preview) > 50:
            preview = preview[:50] + "..."
        return "[" + preview + "]"
    if data_type == "react_element":
        element_type = getattr(value, "type", None)
        name = (
            reconciler._get_component_display_name(element_type)
            if callable(element_type)
            else str(element_type)
        )
        return f"<{name} />"
    if data_type == "typed_array":
        name = getDevtoolsName(reconciler, value)
        size = len(value)
        if short:
            return f"{name}({size})"
        preview = ", ".join(str(item) for item in list(value)[:4])
        if len(value) > 4:
            preview += ", ..."
        if len(preview) > 50:
            preview = preview[:50] + "..."
        return f"{name}({size}) [{preview}]"
    if data_type == "class_instance":
        name = getDevtoolsName(reconciler, value)
        return name or repr(value)
    if data_type == "iterator":
        name = getDevtoolsName(reconciler, value) or "Iterator"
        size = getDevtoolsIteratorSize(reconciler, value)
        if short:
            return f"{name}({size})" if size is not None else name
        items = getDevtoolsIteratorItems(reconciler, value)
        parts: list[str] = []
        for item in items[:4]:
            if isinstance(item, list) and len(item) == 2:
                parts.append(
                    f"{previewDevtoolsValue(reconciler, item[0], short=True)} => {previewDevtoolsValue(reconciler, item[1], short=True)}"
                )
            else:
                parts.append(previewDevtoolsValue(reconciler, item, short=True))
        preview = ", ".join(parts)
        if len(items) > 4:
            preview += ", ..."
        if len(preview) > 50:
            preview = preview[:50] + "..."
        if size is not None:
            return f"{name}({size})" + " {" + preview + "}"
        return name + " {" + preview + "}"
    if data_type == "opaque_iterator":
        return getDevtoolsName(reconciler, value) or "Iterator"
    if data_type == "thenable":
        display_name = getDevtoolsThenableDisplayName(reconciler, value)
        status = getDevtoolsThenableStatus(reconciler, value)
        if status == "fulfilled":
            resolved = getDevtoolsThenableValue(reconciler, value)
            if short:
                return f"fulfilled {display_name} {{…}}"
            if resolved is not None:
                return f"fulfilled {display_name} {{{previewDevtoolsValue(reconciler, resolved, short=True)}}}"
            return f"fulfilled {display_name} {{…}}"
        if status == "rejected":
            reason = getDevtoolsThenableReason(reconciler, value)
            if short:
                return f"rejected {display_name} {{…}}"
            if reason is not None:
                return f"rejected {display_name} {{{previewDevtoolsValue(reconciler, reason, short=True)}}}"
            return f"rejected {display_name} {{…}}"
        if status == "pending":
            return f"pending {display_name}"
        return display_name
    if data_type == "function":
        name = getattr(value, "__name__", "")
        return "() => {}" if not name or name == "<lambda>" else f"{name}() {{}}"
    if data_type == "error":
        preview = f"{type(value).__name__}: {value}"
        return preview if len(preview) <= 50 else preview[:50] + "..."
    return repr(value)


def getDevtoolsName(reconciler: _Reconciler, value: Any) -> str:
    data_type = getDevtoolsDataType(reconciler, value)
    if data_type == "react_lazy":
        return "lazy()"
    if data_type == "html_element":
        return str(getattr(value, "tagName", "div"))
    if data_type == "bigint":
        return str(getattr(value, "value", value))
    if data_type == "unknown":
        return str(getattr(value, "__ink_devtools_unknown_preview__", ""))
    if data_type == "object":
        constructor = getattr(type(value), "__name__", "")
        return "" if constructor == "dict" else constructor
    if data_type == "array":
        return "Array"
    if data_type == "array_buffer":
        return "ArrayBuffer"
    if data_type == "data_view":
        return "DataView"
    if data_type == "typed_array":
        return getattr(type(value), "__name__", "TypedArray")
    if data_type in {"date", "regexp", "symbol"}:
        return str(value)
    if data_type in {"iterator", "opaque_iterator", "html_all_collection"}:
        constructor = getattr(type(value), "__name__", "")
        return constructor or "Iterator"
    if data_type == "react_element":
        element_type = getattr(value, "type", None)
        return (
            reconciler._get_component_display_name(element_type)
            if callable(element_type)
            else str(element_type)
        )
    if data_type == "class_instance":
        constructor = getattr(type(value), "__name__", "")
        return constructor if constructor != "object" else ""
    if data_type == "function":
        return getattr(value, "__name__", "function")
    if data_type == "error":
        return type(value).__name__
    if data_type == "thenable":
        return getDevtoolsThenableDisplayName(reconciler, value)
    return ""


def createDehydratedMetadata(
    reconciler: _Reconciler,
    value: Any,
    *,
    inspectable: bool,
    unserializable: bool,
    inspected: bool = False,
) -> dict[str, Any]:
    data_type = getDevtoolsDataType(reconciler, value)
    metadata = {
        "inspected": inspected,
        "inspectable": inspectable,
        "name": getDevtoolsName(reconciler, value),
        "preview_short": previewDevtoolsValue(reconciler, value, short=True),
        "preview_long": previewDevtoolsValue(reconciler, value, short=False),
        "type": data_type,
    }
    if isinstance(value, (dict, list)):
        metadata["size"] = len(value)
    elif data_type in {"array_buffer", "data_view"}:
        metadata["size"] = getDevtoolsBufferSize(reconciler, value)
    elif data_type == "typed_array":
        metadata["size"] = len(value)
    elif data_type == "iterator":
        size = getDevtoolsIteratorSize(reconciler, value)
        if size is not None:
            metadata["size"] = size
    elif data_type == "class_instance":
        metadata["size"] = len(vars(value))
    if data_type in {"react_element", "error", "class_instance", "iterator", "typed_array"}:
        metadata["readonly"] = True
    if unserializable:
        metadata["unserializable"] = True
    return metadata


def getTransportElementChildren(_reconciler: _Reconciler, element: Any) -> Any:
    children = list(getattr(element, "children", []) or [])
    if not children:
        return None
    if len(children) == 1:
        return children[0]
    return children


def getDevtoolsEnumerableEntries(_reconciler: _Reconciler, value: Any) -> list[tuple[str, Any]]:
    if isinstance(value, dict):
        return [(str(key), item) for key, item in value.items()]
    try:
        return list(vars(value).items())
    except TypeError:
        return []


def getDevtoolsBufferSize(_reconciler: _Reconciler, value: Any) -> int:
    if isinstance(value, memoryview):
        return value.nbytes
    return len(value)


def getDevtoolsIteratorItems(_reconciler: _Reconciler, value: Any) -> list[Any]:
    if isinstance(value, collections_abc.Mapping):
        return [[key, item] for key, item in value.items()]
    if isinstance(value, collections_abc.ItemsView):
        return [[key, item] for key, item in value]
    return list(value)


def getDevtoolsIteratorSize(_reconciler: _Reconciler, value: Any) -> int | None:
    try:
        return len(value)
    except TypeError:
        return None


def getDevtoolsThenableDisplayName(_reconciler: _Reconciler, value: Any) -> str:
    from pyinkcli.packages.react_reconciler.ReactFiberThenable import getThenableDisplayName

    return getThenableDisplayName(value)


def getDevtoolsThenableStatus(_reconciler: _Reconciler, value: Any) -> str:
    from pyinkcli.packages.react_reconciler.ReactFiberThenable import getThenableStatus

    return getThenableStatus(value)


def getDevtoolsThenableValue(_reconciler: _Reconciler, value: Any) -> Any:
    from pyinkcli.packages.react_reconciler.ReactFiberThenable import getThenableValue

    return getThenableValue(value)


def getDevtoolsThenableReason(_reconciler: _Reconciler, value: Any) -> Any:
    from pyinkcli.packages.react_reconciler.ReactFiberThenable import getThenableReason

    return getThenableReason(value)


def getDevtoolsLazyStatus(_reconciler: _Reconciler, payload: Any) -> str | None:
    if payload is None:
        return None
    raw_status = getattr(payload, "_status", None)
    if raw_status == 0:
        return "pending"
    if raw_status == 1:
        return "fulfilled"
    if raw_status == 2:
        return "rejected"
    status = getattr(payload, "status", None)
    return status if isinstance(status, str) else None


def getDevtoolsLazyResolvedValue(_reconciler: _Reconciler, payload: Any) -> Any:
    if payload is None:
        return None
    if getattr(payload, "_status", None) == 1:
        result = getattr(payload, "_result", None)
        default = getattr(result, "default", None)
        return result if default is None else default
    return getattr(payload, "value", None)


def getDevtoolsLazyRejectedValue(_reconciler: _Reconciler, payload: Any) -> Any:
    if payload is None:
        return None
    if getattr(payload, "_status", None) == 2:
        return getattr(payload, "_result", None)
    return getattr(payload, "reason", None)


def createUnserializableTransportValue(
    reconciler: _Reconciler,
    value: Any,
    *,
    root_key: str,
    path: list[Any],
    lookup_path: list[Any],
    cleaned: list[list[Any]],
    unserializable: list[list[Any]],
) -> dict[str, Any]:
    data_type = getDevtoolsDataType(reconciler, value)
    metadata = createDehydratedMetadata(
        reconciler,
        value,
        inspectable=isElement(value)
        or isinstance(value, BaseException)
        or data_type in {"class_instance", "iterator"},
        unserializable=True,
    )
    data_type = metadata["type"]

    if data_type == "react_element":
        metadata["key"] = dehydrateDevtoolsValueForBridge(
            reconciler,
            getattr(value, "key", None),
            root_key=root_key,
            path=[*path, "key"],
            lookup_path=[*lookup_path, "key"],
            cleaned=cleaned,
            unserializable=unserializable,
        )
        element_props = dict(getattr(value, "props", {}))
        children = getTransportElementChildren(reconciler, value)
        if children is not None:
            element_props["children"] = children
        metadata["props"] = dehydrateDevtoolsValueForBridge(
            reconciler,
            element_props,
            root_key=root_key,
            path=[*path, "props"],
            lookup_path=[*lookup_path, "props"],
            cleaned=cleaned,
            unserializable=unserializable,
        )
    elif data_type == "error":
        metadata["message"] = dehydrateDevtoolsValueForBridge(
            reconciler,
            str(value),
            root_key=root_key,
            path=[*path, "message"],
            lookup_path=[*lookup_path, "message"],
            cleaned=cleaned,
            unserializable=unserializable,
        )
        metadata["stack"] = dehydrateDevtoolsValueForBridge(
            reconciler,
            getDevtoolsErrorStack(reconciler, value),
            root_key=root_key,
            path=[*path, "stack"],
            lookup_path=[*lookup_path, "stack"],
            cleaned=cleaned,
            unserializable=unserializable,
        )
        cause = getattr(value, "__cause__", None)
        if cause is not None:
            metadata["cause"] = dehydrateDevtoolsValueForBridge(
                reconciler,
                cause,
                root_key=root_key,
                path=[*path, "cause"],
                lookup_path=[*lookup_path, "cause"],
                cleaned=cleaned,
                unserializable=unserializable,
            )
        for key, item in getDevtoolsEnumerableEntries(reconciler, value):
            if key in {"message", "stack", "cause"}:
                continue
            metadata[key] = dehydrateDevtoolsValueForBridge(
                reconciler,
                item,
                root_key=root_key,
                path=[*path, key],
                lookup_path=[*lookup_path, key],
                cleaned=cleaned,
                unserializable=unserializable,
            )
    elif data_type == "class_instance":
        for key, item in getDevtoolsEnumerableEntries(reconciler, value):
            metadata[key] = dehydrateDevtoolsValueForBridge(
                reconciler,
                item,
                root_key=root_key,
                path=[*path, key],
                lookup_path=[*lookup_path, key],
                cleaned=cleaned,
                unserializable=unserializable,
            )
    elif data_type == "typed_array":
        for index, item in enumerate(list(value)):
            metadata[index] = dehydrateDevtoolsValueForBridge(
                reconciler,
                item,
                root_key=root_key,
                path=[*path, index],
                lookup_path=[root_key],
                cleaned=cleaned,
                unserializable=unserializable,
            )
    elif data_type == "html_all_collection":
        metadata["readonly"] = True
        for index, item in enumerate(getDevtoolsIteratorItems(reconciler, value)):
            metadata[index] = dehydrateDevtoolsValueForBridge(
                reconciler,
                item,
                root_key=root_key,
                path=[*path, index],
                lookup_path=[root_key],
                cleaned=cleaned,
                unserializable=unserializable,
            )
    elif data_type == "iterator":
        for index, item in enumerate(getDevtoolsIteratorItems(reconciler, value)):
            metadata[index] = dehydrateDevtoolsValueForBridge(
                reconciler,
                item,
                root_key=root_key,
                path=[*path, index],
                lookup_path=[root_key],
                cleaned=cleaned,
                unserializable=unserializable,
            )
    elif data_type == "thenable":
        status = getDevtoolsThenableStatus(reconciler, value)
        metadata["name"] = (
            "fulfilled Thenable"
            if status == "fulfilled"
            else "rejected Thenable"
            if status == "rejected"
            else getDevtoolsThenableDisplayName(reconciler, value)
        )
        if status == "fulfilled":
            metadata["value"] = dehydrateDevtoolsValueForBridge(
                reconciler,
                getDevtoolsThenableValue(reconciler, value),
                root_key=root_key,
                path=[*path, "value"],
                lookup_path=[*lookup_path, "value"],
                cleaned=cleaned,
                unserializable=unserializable,
            )
        elif status == "rejected":
            metadata["reason"] = dehydrateDevtoolsValueForBridge(
                reconciler,
                getDevtoolsThenableReason(reconciler, value),
                root_key=root_key,
                path=[*path, "reason"],
                lookup_path=[*lookup_path, "reason"],
                cleaned=cleaned,
                unserializable=unserializable,
            )
    elif data_type == "react_lazy":
        metadata["_payload"] = dehydrateDevtoolsValueForBridge(
            reconciler,
            getattr(value, "_payload", None),
            root_key=root_key,
            path=[*path, "_payload"],
            lookup_path=[*lookup_path, "_payload"],
            cleaned=cleaned,
            unserializable=unserializable,
        )

    return metadata


def isDevtoolsPathInspected(reconciler: _Reconciler, path: list[Any]) -> bool:
    current: Any = reconciler._devtools_currently_inspected_paths
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return False
        current = current[key]
    return True


def shouldExpandDevtoolsPath(
    reconciler: _Reconciler,
    root_key: str,
    lookup_path: list[Any],
) -> bool:
    if len(lookup_path) <= 1:
        return True
    if root_key == "hooks":
        if len(lookup_path) == 2 and isinstance(lookup_path[1], int):
            return True
        if lookup_path[-1] == "subHooks":
            return True
        if len(lookup_path) >= 2 and lookup_path[-2] == "subHooks":
            return True
        if (
            len(lookup_path) >= 2
            and lookup_path[-2] == "hookSource"
            and lookup_path[-1] == "fileName"
        ):
            return True
    elif root_key == "suspendedBy":
        if len(lookup_path) < 5:
            return True
    return isDevtoolsPathInspected(reconciler, lookup_path)


def dehydrateDevtoolsValueForBridge(
    reconciler: _Reconciler,
    value: Any,
    *,
    root_key: str,
    path: list[Any],
    lookup_path: list[Any],
    cleaned: list[list[Any]],
    unserializable: list[list[Any]],
) -> Any:
    data_type = getDevtoolsDataType(reconciler, value)
    if data_type in {"infinity", "nan"}:
        cleaned.append(list(path))
        return {"type": data_type}

    if data_type in {
        "html_element",
        "date",
        "regexp",
        "symbol",
        "bigint",
        "unknown",
        "opaque_iterator",
        "array_buffer",
        "data_view",
    }:
        cleaned.append(list(path))
        return createDehydratedMetadata(
            reconciler,
            value,
            inspectable=False,
            unserializable=False,
        )

    if value is None or isinstance(value, (str, int, float, bool)):
        return cloneDevtoolsValue(reconciler, value)

    if data_type == "thenable":
        status = getDevtoolsThenableStatus(reconciler, value)
        if status not in {"fulfilled", "rejected"}:
            cleaned.append(list(path))
            return createDehydratedMetadata(
                reconciler,
                value,
                inspectable=False,
                unserializable=False,
            )

    if data_type in {
        "react_element",
        "function",
        "error",
        "class_instance",
        "iterator",
        "html_all_collection",
        "typed_array",
        "thenable",
        "react_lazy",
    }:
        unserializable.append(list(path))
        return createUnserializableTransportValue(
            reconciler,
            value,
            root_key=root_key,
            path=path,
            lookup_path=lookup_path,
            cleaned=cleaned,
            unserializable=unserializable,
        )

    if not shouldExpandDevtoolsPath(reconciler, root_key, lookup_path):
        cleaned.append(list(path))
        return createDehydratedMetadata(
            reconciler,
            value,
            inspectable=isinstance(value, (dict, list)) or data_type == "iterator",
            unserializable=False,
        )

    if isinstance(value, dict):
        return {
            key: dehydrateDevtoolsValueForBridge(
                reconciler,
                item,
                root_key=root_key,
                path=[*path, key],
                lookup_path=[*lookup_path, key],
                cleaned=cleaned,
                unserializable=unserializable,
            )
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            dehydrateDevtoolsValueForBridge(
                reconciler,
                item,
                root_key=root_key,
                path=[*path, index],
                lookup_path=[*lookup_path, index],
                cleaned=cleaned,
                unserializable=unserializable,
            )
            for index, item in enumerate(value)
        ]

    cleaned.append(list(path))
    return createDehydratedMetadata(
        reconciler,
        value,
        inspectable=False,
        unserializable=False,
    )


def cleanDevtoolsValueForBridge(
    reconciler: _Reconciler,
    value: Any,
    *,
    root_key: str,
    path: list[Any],
    lookup_path: list[Any] | None = None,
) -> dict[str, Any]:
    cleaned: list[list[Any]] = []
    unserializable: list[list[Any]] = []
    effective_lookup_path = list(path) if lookup_path is None else list(lookup_path)
    data = dehydrateDevtoolsValueForBridge(
        reconciler,
        value,
        root_key=root_key,
        path=path,
        lookup_path=effective_lookup_path,
        cleaned=cleaned,
        unserializable=unserializable,
    )
    return {
        "data": data,
        "cleaned": cleaned,
        "unserializable": unserializable,
    }


def cleanDevtoolsInspectedElementForBridge(
    reconciler: _Reconciler,
    element: dict[str, Any],
) -> dict[str, Any]:
    cleaned = cloneDevtoolsValue(reconciler, element)
    for root_key in ("context", "hooks", "props", "state", "suspendedBy"):
        cleaned[root_key] = cleanDevtoolsValueForBridge(
            reconciler,
            element.get(root_key),
            root_key=root_key,
            path=[],
            lookup_path=[root_key],
        )
    return cleaned


def getDevtoolsErrorStack(_reconciler: _Reconciler, value: BaseException) -> str | None:
    stack = "".join(
        traceback.format_exception(
            type(value),
            value,
            value.__traceback__,
        )
    ).rstrip()
    return stack or None


def getDevtoolsNamedValue(
    reconciler: _Reconciler,
    target: Any,
    key: Any,
) -> tuple[Any, bool]:
    if isinstance(key, int):
        if isinstance(target, array_module.array):
            if key >= len(target):
                return (None, False)
            return (target[key], True)
        if isinstance(target, tuple):
            if key >= len(target):
                return (None, False)
            return (target[key], True)
        if not isinstance(target, list) or key >= len(target):
            return (None, False)
        return (target[key], True)

    if isinstance(target, dict):
        if key not in target:
            return (None, False)
        return (target[key], True)

    if isinstance(target, BaseException):
        if key == "message":
            return (str(target), True)
        if key == "stack":
            return (getDevtoolsErrorStack(reconciler, target), True)
        if key == "cause":
            cause = getattr(target, "__cause__", None)
            return (cause, cause is not None)
        entries = getDevtoolsEnumerableEntries(reconciler, target)
        for entry_key, entry_value in entries:
            if entry_key == key:
                return (entry_value, True)
        return (None, False)

    if hasattr(target, "__dict__"):
        entries = vars(target)
        if key in entries:
            return (entries[key], True)

    target_type = getDevtoolsDataType(reconciler, target)
    if target_type == "thenable":
        if key == "value" and getDevtoolsThenableStatus(reconciler, target) == "fulfilled":
            return (getDevtoolsThenableValue(reconciler, target), True)
        if key == "reason" and getDevtoolsThenableStatus(reconciler, target) == "rejected":
            return (getDevtoolsThenableReason(reconciler, target), True)
    if target_type == "react_lazy" and key == "_payload":
        return (getattr(target, "_payload", None), True)
    if target_type == "typed_array" and isinstance(key, int) and 0 <= key < len(target):
        return (target[key], True)
    if target_type in {"iterator", "html_all_collection"}:
        items = getDevtoolsIteratorItems(reconciler, target)
        if isinstance(key, int) and 0 <= key < len(items):
            return (items[key], True)

    return (None, False)


def getNestedValue(
    reconciler: _Reconciler,
    target: Any,
    path: list[Any],
) -> tuple[Any, bool]:
    current = target
    for key in path:
        current, found = getDevtoolsNamedValue(reconciler, current, key)
        if not found:
            return (None, False)
    return (cloneDevtoolsValue(reconciler, current), True)


def setNestedValue(
    reconciler: _Reconciler,
    target: Any,
    path: list[Any],
    value: Any,
) -> bool:
    if not path:
        if isinstance(value, dict):
            target.clear()
            target.update(cloneDevtoolsValue(reconciler, value))
            return True
        return False
    current: Any = target
    for key in path[:-1]:
        if isinstance(key, int):
            if not isinstance(current, list):
                return False
            while len(current) <= key:
                current.append({})
            if not isinstance(current[key], (dict, list)):
                current[key] = {}
            current = current[key]
            continue
        if not isinstance(current, dict):
            return False
        next_value = current.get(key)
        if not isinstance(next_value, (dict, list)):
            next_value = {}
            current[key] = next_value
        current = next_value
    last_key = path[-1]
    if isinstance(last_key, int):
        if not isinstance(current, list):
            return False
        while len(current) <= last_key:
            current.append(None)
        current[last_key] = cloneDevtoolsValue(reconciler, value)
        return True
    if not isinstance(current, dict):
        return False
    current[last_key] = cloneDevtoolsValue(reconciler, value)
    return True


def deleteNestedValue(
    reconciler: _Reconciler,
    target: dict[str, Any],
    path: list[Any],
) -> bool:
    if not path:
        return False
    parent, key, found = resolveNestedParent(reconciler, target, path)
    if not found:
        return False
    if isinstance(key, int):
        if 0 <= key < len(parent):
            parent.pop(key)
            return True
        return False
    parent.pop(key, None)
    return True


def popNestedValue(
    reconciler: _Reconciler,
    target: dict[str, Any],
    path: list[Any],
) -> tuple[Any, bool]:
    if not path:
        return (None, False)
    parent, key, found = resolveNestedParent(reconciler, target, path)
    if not found:
        return (None, False)
    if isinstance(key, int):
        if 0 <= key < len(parent):
            return (parent.pop(key), True)
        return (None, False)
    return (parent.pop(key), True)


def resolveNestedParent(
    _reconciler: _Reconciler,
    target: dict[str, Any],
    path: list[Any],
) -> tuple[Any, Any, bool]:
    current: Any = target
    for key in path[:-1]:
        if isinstance(key, int):
            if not isinstance(current, list) or key >= len(current):
                return (None, None, False)
            current = current[key]
            continue
        if not isinstance(current, dict) or key not in current:
            return (None, None, False)
        current = current[key]
    return (current, path[-1], True)


def recordDevtoolsInspectedElement(
    reconciler: _Reconciler,
    *,
    node_id: str,
    element_type: str,
    key: str | None,
    props: dict[str, Any] | None = None,
    state: dict[str, Any] | None = None,
    hooks: list[dict[str, Any]] | None = None,
    context: dict[str, Any] | None = None,
    can_edit_hooks: bool = False,
    can_edit_function_props: bool = False,
    can_toggle_error: bool = False,
    is_errored: bool = False,
    can_toggle_suspense: bool = False,
    is_suspended: bool | None = None,
    nearest_error_boundary_id: str | None = None,
    nearest_suspense_boundary_id: str | None = None,
    owners: list[dict[str, Any]] | None = None,
    source: list[Any] | None = None,
    stack: list[list[Any]] | None = None,
    suspended_by: list[Any] | None = None,
) -> None:
    target = reconciler._next_devtools_inspected_elements
    if target is None:
        return
    if nearest_error_boundary_id is not None:
        reconciler._devtools_nearest_error_boundary_by_node[node_id] = nearest_error_boundary_id
    if nearest_suspense_boundary_id is not None:
        reconciler._devtools_nearest_suspense_boundary_by_node[node_id] = nearest_suspense_boundary_id
    target[node_id] = {
        "id": node_id,
        "canEditHooks": can_edit_hooks,
        "canEditFunctionProps": can_edit_function_props,
        "canEditHooksAndDeletePaths": can_edit_hooks,
        "canEditHooksAndRenamePaths": can_edit_hooks,
        "canEditFunctionPropsDeletePaths": can_edit_function_props,
        "canEditFunctionPropsRenamePaths": can_edit_function_props,
        "canToggleError": can_toggle_error,
        "isErrored": is_errored,
        "canToggleSuspense": can_toggle_suspense,
        "isSuspended": is_suspended,
        "hasLegacyContext": False,
        "context": cloneDevtoolsValue(reconciler, context) if context is not None else None,
        "hooks": cloneDevtoolsValue(reconciler, hooks) if hooks is not None else None,
        "props": cloneDevtoolsValue(reconciler, props) if props is not None else None,
        "state": cloneDevtoolsValue(reconciler, state) if state is not None else None,
        "key": key,
        "errors": [],
        "warnings": [],
        "suspendedBy": cloneDevtoolsValue(reconciler, suspended_by)
        if suspended_by is not None
        else [],
        "suspendedByRange": None,
        "unknownSuspenders": 0,
        "owners": cloneDevtoolsValue(reconciler, owners) if owners is not None else None,
        "env": None,
        "source": cloneDevtoolsValue(reconciler, source) if source is not None else None,
        "stack": cloneDevtoolsValue(reconciler, stack) if stack is not None else None,
        "type": element_type,
        "rootType": "pyinkcli",
        "rendererPackageName": packageInfo["name"],
        "rendererVersion": packageInfo["version"],
        "plugins": {"stylex": None},
        "nativeTag": None,
    }
    if suspended_by:
        root_element = target.get("root")
        if isinstance(root_element, dict):
            root_suspended_by = root_element.setdefault("suspendedBy", [])
            if isinstance(root_suspended_by, list):
                root_suspended_by.extend(cloneDevtoolsValue(reconciler, suspended_by))
    fingerprints = reconciler._next_devtools_inspected_element_fingerprints
    if fingerprints is not None:
        fingerprints[node_id] = buildDevtoolsFingerprint(reconciler, target[node_id])
        root_element = target.get("root")
        if isinstance(root_element, dict):
            fingerprints["root"] = buildDevtoolsFingerprint(reconciler, root_element)


def finalizeDevtoolsTreeSnapshot(reconciler: _Reconciler) -> None:
    if reconciler._next_devtools_tree_snapshot is None:
        return

    if reconciler._devtools_most_recently_inspected_id is not None:
        previous_fingerprint = reconciler._devtools_inspected_element_fingerprints.get(
            reconciler._devtools_most_recently_inspected_id
        )
        next_fingerprint = None
        if reconciler._next_devtools_inspected_element_fingerprints is not None:
            next_fingerprint = reconciler._next_devtools_inspected_element_fingerprints.get(
                reconciler._devtools_most_recently_inspected_id
            )
        reconciler._devtools_has_element_updated_since_last_inspected = (
            previous_fingerprint != next_fingerprint
        )

    reconciler._devtools_tree_snapshot = reconciler._next_devtools_tree_snapshot
    reconciler._next_devtools_tree_snapshot = None
    if reconciler._next_devtools_effective_props is not None:
        reconciler._devtools_effective_props = reconciler._next_devtools_effective_props
        reconciler._next_devtools_effective_props = None
    if reconciler._next_devtools_inspected_elements is not None:
        reconciler._devtools_inspected_elements = reconciler._next_devtools_inspected_elements
        reconciler._next_devtools_inspected_elements = None
    if reconciler._next_devtools_inspected_element_fingerprints is not None:
        reconciler._devtools_inspected_element_fingerprints = (
            reconciler._next_devtools_inspected_element_fingerprints
        )
        reconciler._next_devtools_inspected_element_fingerprints = None
    if reconciler._next_devtools_host_instance_ids is not None:
        reconciler._devtools_host_instance_ids = reconciler._next_devtools_host_instance_ids
        reconciler._next_devtools_host_instance_ids = None


__all__ = [
    "buildDevtoolsFingerprint",
    "cleanDevtoolsInspectedElementForBridge",
    "cleanDevtoolsValueForBridge",
    "cloneDevtoolsValue",
    "deleteNestedValue",
    "finalizeDevtoolsTreeSnapshot",
    "getDevtoolsElementValueByPath",
    "getNestedValue",
    "getSerializedDevtoolsElementValueByPath",
    "inspectDevtoolsElement",
    "popNestedValue",
    "recordDevtoolsInspectedElement",
    "setNestedValue",
]
