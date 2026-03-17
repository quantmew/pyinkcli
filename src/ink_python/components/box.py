"""
Box component for ink-python.

A flexbox container component similar to HTML's <div style="display: flex">.
"""

from __future__ import annotations

from typing import Any, Optional, Union

from ink_python.component import VNode, create_vnode
from ink_python.context import (
    get_background_color,
    is_screen_reader_enabled,
    provide_background_color,
)
from ink_python.styles import Styles


def Box(
    *children: Union[VNode, str, None],
    background_color: Optional[str] = None,
    aria_label: Optional[str] = None,
    aria_hidden: bool = False,
    aria_role: Optional[str] = None,
    aria_state: Optional[dict[str, bool]] = None,
    **style: Any,
) -> Optional[VNode]:
    """
    Box component - a flexbox container.

    Like <div style="display: flex"> in the browser.

    Args:
        *children: Child components.
        background_color: Background color for the box.
        aria_label: Accessibility label.
        aria_hidden: Hide from screen readers.
        aria_role: ARIA role.
        aria_state: ARIA state.
        **style: Flexbox style properties.

    Returns:
        A VNode representing the box.
    """
    # Check screen reader mode
    if is_screen_reader_enabled() and aria_hidden:
        return None

    # Build style dict with defaults
    box_style: dict[str, Any] = {
        "flexWrap": "nowrap",
        "flexDirection": "row",
        "flexGrow": 0,
        "flexShrink": 1,
        **style,
    }

    # Handle background color
    if background_color is not None:
        box_style["backgroundColor"] = background_color

    # Handle overflow
    overflow = style.get("overflow", "visible")
    if "overflowX" not in style:
        box_style["overflowX"] = overflow
    if "overflowY" not in style:
        box_style["overflowY"] = overflow

    # Build accessibility info
    accessibility = {}
    if aria_role:
        accessibility["role"] = aria_role
    if aria_state:
        accessibility["state"] = aria_state

    # Handle children - add label for screen readers
    actual_children: list[Union[VNode, str, None]] = []
    if is_screen_reader_enabled() and aria_label:
        actual_children.append(create_vnode("ink-text", aria_label))
    else:
        actual_children.extend(children)

    # Create the box element
    box_element = create_vnode(
        "ink-box",
        *actual_children,
        style=box_style,
        internal_accessibility=accessibility,
    )

    # Provide background color context
    if background_color:
        with provide_background_color(background_color):
            return box_element

    return box_element


def box(
    *children: Union[VNode, str, None],
    **kwargs: Any,
) -> Optional[VNode]:
    """
    Lowercase alias for Box component.

    Args:
        *children: Child components.
        **kwargs: Box properties.

    Returns:
        A VNode representing the box.
    """
    return Box(*children, **kwargs)
