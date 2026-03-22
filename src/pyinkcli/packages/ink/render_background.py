"""Background rendering helpers."""

from __future__ import annotations

from pyinkcli.colorize import colorize
from pyinkcli.packages.ink.layout_utils import safe_yoga_int


def renderBackground(x: int, y: int, node, output) -> None:
    background_color = node.style.get("backgroundColor")
    if not background_color or node.yogaNode is None:
        return

    width = safe_yoga_int(node, "get_computed_width")
    height = safe_yoga_int(node, "get_computed_height")
    if width is None or height is None or width <= 0 or height <= 0:
        return
    left_border = 1 if node.style.get("borderStyle") and node.style.get("borderLeft", True) is not False else 0
    right_border = 1 if node.style.get("borderStyle") and node.style.get("borderRight", True) is not False else 0
    top_border = 1 if node.style.get("borderStyle") and node.style.get("borderTop", True) is not False else 0
    bottom_border = 1 if node.style.get("borderStyle") and node.style.get("borderBottom", True) is not False else 0
    content_width = max(0, width - left_border - right_border)
    content_height = max(0, height - top_border - bottom_border)
    if content_width == 0 or content_height == 0:
        return

    line = colorize(" " * content_width, background_color, "background")
    for row in range(content_height):
        output.write(x + left_border, y + top_border + row, line, {"transformers": []})
