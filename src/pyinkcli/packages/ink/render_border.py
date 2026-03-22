"""Border rendering helpers."""

from __future__ import annotations

from pyinkcli.colorize import colorize
from pyinkcli.packages.ink.layout_utils import safe_yoga_int
from pyinkcli.utils.cli_boxes import get_box_style


def renderBorder(x: int, y: int, node, output) -> None:
    border_style = node.style.get("borderStyle")
    if not border_style or node.yogaNode is None:
        return

    width = safe_yoga_int(node, "get_computed_width")
    height = safe_yoga_int(node, "get_computed_height")
    if width is None or height is None or width <= 0 or height <= 0:
        return
    box = get_box_style(border_style)

    show_top = node.style.get("borderTop", True) is not False
    show_bottom = node.style.get("borderBottom", True) is not False
    show_left = node.style.get("borderLeft", True) is not False
    show_right = node.style.get("borderRight", True) is not False
    content_width = max(0, width - (1 if show_left else 0) - (1 if show_right else 0))

    border_color = node.style.get("borderColor")
    if show_top:
        top = (box.top_left if show_left else "") + box.top * content_width + (box.top_right if show_right else "")
        output.write(x, y, colorize(top, border_color, "foreground"), {"transformers": []})
    if show_bottom:
        bottom = (box.bottom_left if show_left else "") + box.bottom * content_width + (box.bottom_right if show_right else "")
        output.write(x, y + height - 1, colorize(bottom, border_color, "foreground"), {"transformers": []})

    vertical_height = max(0, height - (1 if show_top else 0) - (1 if show_bottom else 0))
    if show_left:
        output.write(x, y + (1 if show_top else 0), "\n".join(colorize(box.left, border_color, "foreground") for _ in range(vertical_height)), {"transformers": []})
    if show_right:
        output.write(x + width - 1, y + (1 if show_top else 0), "\n".join(colorize(box.right, border_color, "foreground") for _ in range(vertical_height)), {"transformers": []})
