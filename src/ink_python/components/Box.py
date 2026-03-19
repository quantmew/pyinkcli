"""
Box component for ink-python.

Canonical component module matching JS basename.
"""

from __future__ import annotations

from typing import Any, Optional

from ink_python._component_runtime import RenderableNode, createElement, scopeRender
from ink_python.components._accessibility_runtime import _is_screen_reader_enabled
from ink_python.components._background_runtime import _provide_background_color


def _resolve_background_color(
    background_color: Optional[str],
    style: dict[str, Any],
) -> tuple[bool, Optional[str]]:
    if background_color is not None:
        return True, background_color

    if "backgroundColor" in style:
        return True, style["backgroundColor"]

    return False, None

def Box(
    *children: RenderableNode,
    background_color: Optional[str] = None,
    aria_label: Optional[str] = None,
    aria_hidden: bool = False,
    aria_role: Optional[str] = None,
    aria_state: Optional[dict[str, bool]] = None,
    **style: Any,
) -> RenderableNode:
    is_screen_reader_enabled = _is_screen_reader_enabled()
    if is_screen_reader_enabled and aria_hidden:
        return None

    has_explicit_background, resolved_background = _resolve_background_color(
        background_color,
        style,
    )
    box_style: dict[str, Any] = {
        "flexWrap": "nowrap",
        "flexDirection": "row",
        "flexGrow": 0,
        "flexShrink": 1,
        **style,
    }
    if has_explicit_background:
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
    if is_screen_reader_enabled and aria_label:
        actual_children.append(createElement("ink-text", aria_label))
    else:
        actual_children.extend(children)

    box_element = createElement(
        "ink-box",
        *actual_children,
        style=box_style,
        internal_accessibility=accessibility,
    )

    if has_explicit_background:
        return scopeRender(
            box_element,
            lambda: _provide_background_color(resolved_background),
        )

    return box_element


__all__ = ["Box"]
