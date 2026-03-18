"""
Box component for ink-python.

Canonical component module matching JS basename.
"""

from __future__ import annotations

from typing import Any, Optional

from ink_python._component_runtime import RenderableNode, createElement
from ink_python.components._accessibility_runtime import _is_screen_reader_enabled
from ink_python.components._background_runtime import (
    _get_background_color,
    _provide_background_color,
)

def Box(
    *children: RenderableNode,
    background_color: Optional[str] = None,
    aria_label: Optional[str] = None,
    aria_hidden: bool = False,
    aria_role: Optional[str] = None,
    aria_state: Optional[dict[str, bool]] = None,
    **style: Any,
) -> RenderableNode:
    if _is_screen_reader_enabled() and aria_hidden:
        return None

    box_style: dict[str, Any] = {
        "flexWrap": "nowrap",
        "flexDirection": "row",
        "flexGrow": 0,
        "flexShrink": 1,
        **style,
    }

    inherited_background = _get_background_color()
    resolved_background = background_color if background_color is not None else inherited_background
    if resolved_background is not None:
        box_style["backgroundColor"] = resolved_background

    overflow = style.get("overflow", "visible")
    if "overflowX" not in style:
        box_style["overflowX"] = overflow
    if "overflowY" not in style:
        box_style["overflowY"] = overflow

    accessibility: dict[str, Any] = {}
    if aria_role:
        accessibility["role"] = aria_role
    if aria_state:
        accessibility["state"] = aria_state

    actual_children: list[RenderableNode] = []
    if _is_screen_reader_enabled() and aria_label:
        actual_children.append(createElement("ink-text", aria_label))
    else:
        actual_children.extend(children)

    box_element = createElement(
        "ink-box",
        *actual_children,
        style=box_style,
        internal_accessibility=accessibility,
    )

    if resolved_background:
        with _provide_background_color(resolved_background):
            return box_element

    return box_element


__all__ = ["Box"]
