from __future__ import annotations

from typing import Any

from ..component import RenderableNode, isElement


def _clone_element_with_key(element: RenderableNode, key: str) -> RenderableNode:
    return RenderableNode(
        type=element.type,
        props=dict(element.props),
        children=list(element.children),
        key=key,
    )


def children_to_array(children: Any, *, keep_primitives: bool = False, prefix: str = "") -> list[Any]:
    result: list[Any] = []
    if children is None:
        return result
    if isinstance(children, (list, tuple)):
        for index, child in enumerate(children):
            next_prefix = f".{index}" if not prefix else f"{prefix}:{index}"
            result.extend(children_to_array(child, keep_primitives=keep_primitives, prefix=next_prefix))
        return result
    if isElement(children):
        if children.key is not None:
            if prefix.startswith(".") and prefix.count(":") == 0:
                computed_key = f".$%s" % children.key
            elif prefix:
                parent_prefix = prefix.rsplit(":", 1)[0] if ":" in prefix else ""
                computed_key = f"{parent_prefix}:$%s" % children.key if parent_prefix else f".$%s" % children.key
            else:
                computed_key = f".$%s" % children.key
        else:
            computed_key = prefix or ".0"
        result.append(_clone_element_with_key(children, computed_key))
        return result
    if keep_primitives:
        result.append(children)
    return result


def create_children_api():
    return {
        "toArray": lambda children: children_to_array(children),
        "map": lambda children, fn: [fn(child, index) for index, child in enumerate(children_to_array(children))],
        "count": lambda children: len(children_to_array(children, keep_primitives=True)),
        "only": lambda child: child,
    }


__all__ = ["children_to_array", "create_children_api"]
