from __future__ import annotations

from ..component import createElement


def Box(*children, **props):
    style = {
        "flexWrap": "nowrap",
        "flexDirection": "row",
        "flexGrow": 0,
        "flexShrink": 1,
    }
    if "background_color" in props and "backgroundColor" not in props:
        props["backgroundColor"] = props["background_color"]
    if "paddingX" in props:
        props["padding_x"] = props["paddingX"]
    if "paddingY" in props:
        props["padding_y"] = props["paddingY"]
    for key in (
        "flexDirection",
        "padding",
        "margin",
        "width",
        "height",
        "borderStyle",
        "backgroundColor",
        "borderColor",
        "padding_x",
        "padding_y",
    ):
        if key in props:
            style[key] = props[key]
    if "overflow" in props:
        style["overflowX"] = props["overflow"]
        style["overflowY"] = props["overflow"]
    next_props = dict(props)
    next_props["style"] = style
    return createElement("ink-box", *children, **next_props)


__all__ = ["Box"]
