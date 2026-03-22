"""React element helpers."""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

from pyinkcli._component_runtime import _Element, _ScopedNode, _create_element_record, _is_element_record, _is_scoped_node, createElement as _create_element


class Ref:
    def __init__(self, current: Any = None) -> None:
        self.current = current


def createRef() -> Ref:
    return Ref()


def createElement(
    type: str | Callable | type,
    *children: Any,
    key: str | None = None,
    **props: Any,
):
    return _create_element(type, *children, key=key, **props)


def cloneAndReplaceKey(element: Any, key: str | None):
    if not isValidElement(element):
        raise TypeError("cloneAndReplaceKey expects a React element")
    return _create_element(
        element.type,
        *element.children,
        key=key,
        **dict(element.props),
    )


def cloneElement(element: Any, *children: Any, key: str | None = None, **props: Any):
    if not isValidElement(element):
        raise TypeError("cloneElement expects a React element")

    merged_props = dict(element.props)
    merged_props.update(props)
    final_key = key if key is not None else element.key
    final_children = children if children else tuple(element.children)
    return _create_element(
        element.type,
        *final_children,
        key=final_key,
        **merged_props,
    )


def isValidElement(value: Any) -> bool:
    return _is_element_record(value)


__all__ = [
    "createElement",
    "cloneElement",
    "cloneAndReplaceKey",
    "isValidElement",
    "createRef",
    "Ref",
]
