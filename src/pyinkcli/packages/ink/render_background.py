"""Background renderer for the internal Ink host view package."""

from __future__ import annotations

from pyinkcli.packages.ink.dom import DOMElement
from pyinkcli.packages.ink.output import Output


def renderBackground(x: int, y: int, node: DOMElement, output: Output) -> None:
    """Render the background color for a box."""
    bg_color = node.style.get("backgroundColor")
    if not bg_color:
        return

    yoga_node = node.yogaNode
    if yoga_node is None:
        return

    width = int(yoga_node.get_computed_width())
    height = int(yoga_node.get_computed_height())

    left_border_width = 1 if node.style.get("borderStyle") and node.style.get("borderLeft", True) else 0
    right_border_width = 1 if node.style.get("borderStyle") and node.style.get("borderRight", True) else 0
    top_border_height = 1 if node.style.get("borderStyle") and node.style.get("borderTop", True) else 0
    bottom_border_height = 1 if node.style.get("borderStyle") and node.style.get("borderBottom", True) else 0

    content_width = width - left_border_width - right_border_width
    content_height = height - top_border_height - bottom_border_height
    if not (content_width > 0 and content_height > 0):
        return

    from pyinkcli.colorize import colorize

    background_line = colorize(" " * content_width, bg_color, "background")
    for row in range(content_height):
        output.write(
            x + left_border_width,
            y + top_border_height + row,
            background_line,
            transformers=[],
        )
