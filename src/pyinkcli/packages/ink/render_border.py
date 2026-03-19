"""Border renderer for the internal Ink host view package."""

from __future__ import annotations

from pyinkcli.packages.ink.dom import DOMElement
from pyinkcli.packages.ink.output import Output


def renderBorder(x: int, y: int, node: DOMElement, output: Output) -> None:
    """Render the border for a box."""
    border_style = node.style.get("borderStyle")
    if not border_style:
        return

    yoga_node = node.yogaNode
    if yoga_node is None:
        return

    from pyinkcli.colorize import colorize
    from pyinkcli.utils.cli_boxes import get_box_style

    try:
        box = get_box_style(border_style)
    except KeyError:
        return

    width = int(yoga_node.get_computed_width())
    height = int(yoga_node.get_computed_height())

    top_border_color = node.style.get("borderTopColor", node.style.get("borderColor"))
    bottom_border_color = node.style.get("borderBottomColor", node.style.get("borderColor"))
    left_border_color = node.style.get("borderLeftColor", node.style.get("borderColor"))
    right_border_color = node.style.get("borderRightColor", node.style.get("borderColor"))

    dim_top_border_color = node.style.get("borderTopDimColor", node.style.get("borderDimColor", False))
    dim_bottom_border_color = node.style.get("borderBottomDimColor", node.style.get("borderDimColor", False))
    dim_left_border_color = node.style.get("borderLeftDimColor", node.style.get("borderDimColor", False))
    dim_right_border_color = node.style.get("borderRightDimColor", node.style.get("borderDimColor", False))

    show_top_border = node.style.get("borderTop", True)
    show_bottom_border = node.style.get("borderBottom", True)
    show_left_border = node.style.get("borderLeft", True)
    show_right_border = node.style.get("borderRight", True)

    content_width = width - (1 if show_left_border else 0) - (1 if show_right_border else 0)

    def maybe_dim(text: str, enabled: bool) -> str:
        return f"\x1b[2m{text}\x1b[22m" if enabled else text

    top_border = None
    if show_top_border:
        top_border = colorize(
            (box.top_left if show_left_border else "")
            + box.top * content_width
            + (box.top_right if show_right_border else ""),
            top_border_color,
            "foreground",
        )
        top_border = maybe_dim(top_border, bool(dim_top_border_color))

    bottom_border = None
    if show_bottom_border:
        bottom_border = colorize(
            (box.bottom_left if show_left_border else "")
            + box.bottom * content_width
            + (box.bottom_right if show_right_border else ""),
            bottom_border_color,
            "foreground",
        )
        bottom_border = maybe_dim(bottom_border, bool(dim_bottom_border_color))

    vertical_height = height - (1 if show_top_border else 0) - (1 if show_bottom_border else 0)
    left_border = maybe_dim(colorize(box.left, left_border_color, "foreground"), bool(dim_left_border_color))
    right_border = maybe_dim(colorize(box.right, right_border_color, "foreground"), bool(dim_right_border_color))
    offset_y = 1 if show_top_border else 0

    if top_border:
        output.write(x, y, top_border, transformers=[])

    for row in range(vertical_height):
        if show_left_border:
            output.write(x, y + offset_y + row, left_border, transformers=[])
        if show_right_border:
            output.write(x + width - 1, y + offset_y + row, right_border, transformers=[])

    if bottom_border:
        output.write(x, y + height - 1, bottom_border, transformers=[])
