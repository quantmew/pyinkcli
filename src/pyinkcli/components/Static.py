from __future__ import annotations

from ..component import createElement
from ..hooks import useLayoutEffect, useRef


def Static(*children, **props):
    props = dict(props)
    props["internal_static"] = True
    items = props.pop("items", None)
    render_item = props.pop("renderItem", None)
    custom_style = props.pop("style", None)
    if render_item is None and children and callable(children[0]):
        render_item = children[0]
        children = children[1:]
    index_ref = useRef(0)

    if items is None:
        items = []

    def sync_index():
        index_ref.current = len(items)
        return None

    useLayoutEffect(sync_index, (len(items),))

    rendered_items = []
    if items is not None and callable(render_item):
        start_index = index_ref.current if len(items) >= index_ref.current else 0
        items_to_render = list(items[start_index:])
        rendered_items = [
            render_item(item, start_index + item_index)
            for item_index, item in enumerate(items_to_render)
        ]

    style = {
        "position": "absolute",
        "flexDirection": "column",
    }
    if isinstance(custom_style, dict):
        style.update(custom_style)
    props["style"] = style

    return createElement("ink-box", *(rendered_items or children), **props)


__all__ = ["Static"]
