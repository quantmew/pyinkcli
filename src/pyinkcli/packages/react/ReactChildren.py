"""React.Children compatibility helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from pyinkcli.packages.react.jsx.ReactJSXElement import (
    cloneAndReplaceKey,
    cloneElement,
    isValidElement,
)


def _walk(children: Any):
    if children is None or children is False or children is True:
        return
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from _walk(child)
        return
    if isinstance(children, Iterable) and not isinstance(children, (str, bytes, dict)) and not isValidElement(children):
        for child in children:
            yield from _walk(child)
        return
    yield children


def _to_array(children: Any, path: str = "", parent_prefix: str = "") -> list[Any]:
    if children is None or children is False or children is True:
        return []
    if isinstance(children, (list, tuple)):
        flattened: list[Any] = []
        for index, child in enumerate(children):
            next_path = f"{path}:{index}" if path else str(index)
            flattened.extend(_to_array(child, next_path, path))
        return flattened
    if isinstance(children, Iterable) and not isinstance(children, (str, bytes, dict)) and not isValidElement(children):
        return _to_array(list(children), path, parent_prefix)
    if isValidElement(children):
        if children.key is not None:
            computed = f".{parent_prefix}:${children.key}" if parent_prefix else f".${children.key}"
        else:
            computed = f".{path}" if path else None
        return [cloneAndReplaceKey(children, computed)]
    return [children]


def toArray(children: Any) -> list[Any]:
    return _to_array(children)


def count(children: Any) -> int:
    return len(list(_walk(children)))


def forEach(children: Any, fn: Callable[[Any, int], None]) -> None:
    for index, child in enumerate(toArray(children)):
        fn(child, index)


def map(children: Any, fn: Callable[[Any, int], Any]) -> list[Any]:
    mapped: list[Any] = []
    for index, child in enumerate(toArray(children)):
        result = fn(child, index)
        if result is None:
            continue
        if isinstance(result, (list, tuple)):
            mapped.extend(result)
        else:
            mapped.append(result)
    return mapped


def only(children: Any) -> Any:
    items = list(_walk(children))
    if len(items) != 1:
        raise ValueError("React.Children.only expected to receive a single child.")
    return items[0]


class _ChildrenFacade(dict):
    def __getattr__(self, name: str) -> Any:
        return self[name]


Children = _ChildrenFacade(
    map=map,
    forEach=forEach,
    count=count,
    toArray=toArray,
    only=only,
)


__all__ = ["Children", "map", "forEach", "count", "toArray", "only", "cloneElement"]
