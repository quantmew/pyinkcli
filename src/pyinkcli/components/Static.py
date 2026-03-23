from __future__ import annotations

from ..component import createElement


def Static(*children, **props):
    props = dict(props)
    props["internal_static"] = True
    items = props.pop("items", None)
    render_item = props.pop("renderItem", None)
    if render_item is None and children and callable(children[0]):
        render_item = children[0]
        children = children[1:]
    rendered_items = []
    if items is not None and callable(render_item):
        rendered_items = [render_item(item, index) for index, item in enumerate(items)]
    return createElement("ink-box", *(rendered_items or children), **props)


__all__ = ["Static"]
