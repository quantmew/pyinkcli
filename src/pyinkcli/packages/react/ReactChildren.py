"""Children helpers aligned more closely with ReactChildren traversal semantics."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from pyinkcli._component_runtime import _Element, _ScopedNode, isElement

SEPARATOR = "."
SUBSEPARATOR = ":"


def _is_iterable_children(value: Any) -> bool:
    return (
        isinstance(value, Iterable)
        and not isinstance(value, (str, bytes))
        and not isElement(value)
    )


def _escape_key(key: str) -> str:
    return "$" + key.replace("=", "=0").replace(":", "=2")


def _escape_user_provided_key(text: str) -> str:
    return text.replace("/", "//")


def _to_base36(index: int) -> str:
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    if index == 0:
        return "0"
    value = index
    parts: list[str] = []
    while value:
        value, remainder = divmod(value, 36)
        parts.append(chars[remainder])
    return "".join(reversed(parts))


def _get_element_key(element: Any, index: int) -> str:
    if isElement(element):
        key = getattr(element, "key", None)
        if key is not None:
            return _escape_key(str(key))
    return _to_base36(index)


def _clone_and_replace_key(element: Any, key: str) -> Any:
    if isinstance(element, _Element):
        clone = object.__new__(_Element)
        clone.type = element.type
        clone.props = dict(element.props)
        clone.children = list(element.children)
        clone.key = key
        return clone
    if isinstance(element, _ScopedNode):
        clone = object.__new__(_ScopedNode)
        clone.node = _clone_and_replace_key(element.node, key)
        clone.context_manager_factories = tuple(element.context_manager_factories)
        return clone
    return element


def _map_into_array(
    children: Any,
    array: list[Any],
    escaped_prefix: str,
    name_so_far: str,
    callback: Callable[[Any], Any],
) -> int:
    if children is None:
        return 0
    if isinstance(children, bool):
        children = None

    invoke_callback = False
    if children is None:
        invoke_callback = True
    elif isinstance(children, (str, int, float)):
        invoke_callback = True
    elif isElement(children):
        invoke_callback = True

    if invoke_callback:
        mapped_child = callback(children)
        child_key = (
            name_so_far
            if name_so_far != ""
            else SEPARATOR + _get_element_key(children, 0)
        )

        if _is_iterable_children(mapped_child):
            escaped_child_key = ""
            if child_key:
                escaped_child_key = _escape_user_provided_key(child_key) + "/"
            nested_count = 0
            for index, item in enumerate(mapped_child):
                nested_count += _map_into_array(
                    item,
                    array,
                    escaped_prefix + escaped_child_key,
                    "",
                    lambda value: value,
                )
            return nested_count

        if mapped_child is not None:
            if isElement(mapped_child):
                mapped_key = getattr(mapped_child, "key", None)
                mapped_child = _clone_and_replace_key(
                    mapped_child,
                    escaped_prefix
                    + (
                        _escape_user_provided_key(str(mapped_key)) + "/"
                        if mapped_key is not None
                        and (children is None or mapped_key != getattr(children, "key", None))
                        else ""
                    )
                    + child_key,
                )
            array.append(mapped_child)
            return 1
        return 0

    if _is_iterable_children(children):
        subtree_count = 0
        next_name_prefix = name_so_far + SUBSEPARATOR if name_so_far else SEPARATOR
        for index, child in enumerate(children):
            next_name = next_name_prefix + _get_element_key(child, index)
            subtree_count += _map_into_array(
                child,
                array,
                escaped_prefix,
                next_name,
                callback,
            )
        return subtree_count

    mapped_child = callback(children)
    if mapped_child is not None:
        array.append(mapped_child)
        return 1
    return 0


def map(children: Any, fn: Callable[[Any, int], Any]) -> list[Any]:
    result: list[Any] = []
    index = 0

    def apply(child: Any) -> Any:
        nonlocal index
        mapped = fn(child, index)
        index += 1
        return mapped

    _map_into_array(children, result, "", "", apply)
    return result


def forEach(children: Any, fn: Callable[[Any, int], Any]) -> None:
    map(children, fn)


def count(children: Any) -> int:
    total = 0

    def apply(child: Any) -> Any:
        nonlocal total
        total += 1
        return None

    _map_into_array(children, [], "", "", apply)
    return total


def toArray(children: Any) -> list[Any]:
    result: list[Any] = []
    _map_into_array(children, result, "", "", lambda child: child)
    return result


def only(children: Any) -> Any:
    if not isElement(children):
        raise ValueError("React.Children.only expected to receive a single React element child.")
    return children


__all__ = ["count", "forEach", "map", "only", "toArray"]
