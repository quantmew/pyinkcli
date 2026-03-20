from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from pyinkcli._component_runtime import RenderableNode, createElement
from pyinkcli.hooks._runtime import useRef


def _StaticComponent(
    *,
    items: list[Any],
    render_item: Callable[[Any, int], RenderableNode] | None,
    box_style: dict[str, Any],
) -> RenderableNode:
    index_ref = useRef(0)
    start_index = int(index_ref.current or 0)
    items_to_render = items[start_index:]
    index_ref.current = len(items)

    children: list[RenderableNode] = []
    if render_item is not None:
        children.extend(
            render_item(item, start_index + item_index)
            for item_index, item in enumerate(items_to_render)
        )
    else:
        children.extend(items_to_render)

    return createElement(
        "ink-box",
        *children,
        internal_static=True,
        style=box_style,
    )


def Static(
    *children: Any,
    items: Iterable[Any] | None = None,
    renderItem: Callable[[Any, int], RenderableNode] | None = None,
    **props: Any,
) -> RenderableNode:
    actual_children = list(children)
    inferred_renderer = renderItem

    if items is None:
        return createElement("ink-box", *actual_children, internal_static=True, **props)

    items_list = list(items)

    if len(actual_children) == 1 and callable(actual_children[0]) and inferred_renderer is None:
        inferred_renderer = actual_children.pop(0)

    box_style = {
        "position": "absolute",
        "flexDirection": "column",
        **props,
    }
    return createElement(
        _StaticComponent,
        items=items_list,
        render_item=inferred_renderer,
        box_style=box_style,
    )


__all__ = ["Static"]
