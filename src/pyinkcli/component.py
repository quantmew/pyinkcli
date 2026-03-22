from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RenderableNode:
    type: Any
    props: dict[str, Any] = field(default_factory=dict)
    children: list[Any] = field(default_factory=list)
    key: str | None = None


def _flatten_children(values: tuple[Any, ...]) -> list[Any]:
    flattened: list[Any] = []
    for value in values:
        if value is None or value is False:
            continue
        if isinstance(value, (list, tuple)):
            flattened.extend(_flatten_children(tuple(value)))
        else:
            flattened.append(value)
    return flattened


def createElement(type_: Any, *children: Any, **props: Any) -> RenderableNode:
    props = dict(props)
    key = props.pop("key", None)
    return RenderableNode(type=type_, props=props, children=_flatten_children(children), key=key)


def component(fn):
    return fn


def isElement(value: Any) -> bool:
    return isinstance(value, RenderableNode)


__all__ = ["createElement", "component", "isElement", "RenderableNode"]

