"""
measure_element for pyinkcli.

Measure the dimensions of a Box element.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyinkcli.packages.ink.dom import DOMElement


@dataclass
class ElementDimensions:
    """Dimensions of a measured element."""

    width: int
    height: int


def measureElement(node: DOMElement) -> ElementDimensions:
    """
    Measure the dimensions of a Box element.

    Returns an object with width and height properties.
    This function is useful when your component needs to know
    the amount of available space it has.

    Note: measureElement() returns ElementDimensions(0, 0) when called
    during render (before layout is calculated). Call it from post-render
    code, such as useEffect, input handlers, or timer callbacks.

    Args:
        node: The DOM element to measure.

    Returns:
        ElementDimensions with width and height.

    Example:
        >>> @component
        ... def ResizableBox():
        ...     state = use_app()
        ...     def on_layout():
        ...         dims = measureElement(state.context)
        ...         print(f"Width: {dims.width}, Height: {dims.height}")
        ...     return createElement(Box, onLayout=on_layout)
    """
    yoga_node = node.yoga_node
    if yoga_node is None:
        return ElementDimensions(width=0, height=0)

    return ElementDimensions(
        width=int(yoga_node.get_computed_width()),
        height=int(yoga_node.get_computed_height()),
    )
