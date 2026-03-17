"""
Render nodes to output for ink-python.

Converts DOM nodes to terminal output.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

from ink_python import yoga_compat as yoga

from ink_python.dom import DOMElement, TextNode, DOMNode, squash_text_nodes
from ink_python.measure_text import measure_text
from ink_python.wrap_text import wrap_text
from ink_python.utils.string_width import widest_line
from ink_python.output import Output

if TYPE_CHECKING:
    pass

# Output transformer type
OutputTransformer = Callable[[str, int], str]


def apply_padding_to_text(node: DOMElement, text: str) -> str:
    """Apply padding offset to text."""
    if node.child_nodes:
        first_child = node.child_nodes[0]
        if hasattr(first_child, "yoga_node") and first_child.yoga_node:
            offset_x = first_child.yoga_node.get_computed_left()
            offset_y = first_child.yoga_node.get_computed_top()
            text = "\n" * offset_y + indent_string(text, offset_x)
    return text


def indent_string(text: str, count: int) -> str:
    """Indent each line of text."""
    if count <= 0:
        return text
    indent = " " * count
    return "\n".join(indent + line for line in text.split("\n"))


def get_max_width(yoga_node) -> int:
    """Get the maximum content width for a node."""
    width = yoga_node.get_computed_width()
    padding_left = yoga_node.get_computed_padding(yoga.EDGE_LEFT)
    padding_right = yoga_node.get_computed_padding(yoga.EDGE_RIGHT)
    border_left = yoga_node.get_computed_border(yoga.EDGE_LEFT)
    border_right = yoga_node.get_computed_border(yoga.EDGE_RIGHT)

    return int(width - padding_left - padding_right - border_left - border_right)


def render_node_to_output(
    node: DOMElement,
    output: Output,
    *,
    offset_x: int = 0,
    offset_y: int = 0,
    transformers: Optional[list[OutputTransformer]] = None,
    skip_static_elements: bool = False,
) -> None:
    """
    Render a DOM node to the output buffer.

    Args:
        node: The DOM node to render.
        output: The output buffer.
        offset_x: X offset from parent.
        offset_y: Y offset from parent.
        transformers: List of text transformers.
        skip_static_elements: Whether to skip static elements.
    """
    if skip_static_elements and node.internal_static:
        return

    yoga_node = node.yoga_node
    if yoga_node is None:
        return

    if yoga_node.get_display() == yoga.DISPLAY_NONE:
        return

    # Calculate position
    x = int(offset_x + yoga_node.get_computed_left())
    y = int(offset_y + yoga_node.get_computed_top())

    # Build transformer list
    new_transformers = list(transformers or [])
    if node.internal_transform is not None:
        new_transformers.insert(0, node.internal_transform)

    # Handle text nodes
    if node.node_name == "ink-text":
        text = squash_text_nodes(node)
        if text:
            current_width = widest_line(text)
            max_width = get_max_width(yoga_node)

            if current_width > max_width:
                text_wrap = node.style.get("textWrap", "wrap")
                text = wrap_text(text, max_width, text_wrap)

            text = apply_padding_to_text(node, text)
            output.write(x, y, text, transformers=new_transformers)
        return

    # Handle box elements
    clip_horizontal = False
    clip_vertical = False

    if node.node_name == "ink-box":
        # Render background
        render_background(x, y, node, output)

        # Render border
        render_border(x, y, node, output)

        # Handle clipping
        clip_horizontal = (
            node.style.get("overflowX") == "hidden"
            or node.style.get("overflow") == "hidden"
        )
        clip_vertical = (
            node.style.get("overflowY") == "hidden"
            or node.style.get("overflow") == "hidden"
        )

        if clip_horizontal or clip_vertical:
            x1 = (
                x + yoga_node.get_computed_border(yoga.EDGE_LEFT)
                if clip_horizontal
                else None
            )
            x2 = (
                x
                + yoga_node.get_computed_width()
                - yoga_node.get_computed_border(yoga.EDGE_RIGHT)
                if clip_horizontal
                else None
            )
            y1 = (
                y + yoga_node.get_computed_border(yoga.EDGE_TOP)
                if clip_vertical
                else None
            )
            y2 = (
                y
                + yoga_node.get_computed_height()
                - yoga_node.get_computed_border(yoga.EDGE_BOTTOM)
                if clip_vertical
                else None
            )

            output.clip(x1=x1, x2=x2, y1=y1, y2=y2)

    # Render children
    if node.node_name in ("ink-root", "ink-box"):
        for child in node.child_nodes:
            if isinstance(child, DOMElement):
                render_node_to_output(
                    child,
                    output,
                    offset_x=x,
                    offset_y=y,
                    transformers=new_transformers,
                    skip_static_elements=skip_static_elements,
                )

        # Unclip if we clipped
        if clip_horizontal or clip_vertical:
            output.unclip()


def render_background(x: int, y: int, node: DOMElement, output: Output) -> None:
    """Render the background color for a box."""
    bg_color = node.style.get("backgroundColor")
    if not bg_color:
        return

    yoga_node = node.yoga_node
    if yoga_node is None:
        return

    width = int(yoga_node.get_computed_width())
    height = int(yoga_node.get_computed_height())

    # Create background string
    from ink_python.colorize import colorize

    def bg_transform(s: str, index: int) -> str:
        return colorize(s, bg_color, "background")

    # Fill the background area
    for row in range(height):
        output.write(x, y + row, " " * width, transformers=[bg_transform])


def render_border(x: int, y: int, node: DOMElement, output: Output) -> None:
    """Render the border for a box."""
    border_style = node.style.get("borderStyle")
    if not border_style:
        return

    yoga_node = node.yoga_node
    if yoga_node is None:
        return

    from ink_python.utils.cli_boxes import get_box_style
    from ink_python.colorize import colorize

    try:
        box = get_box_style(border_style)
    except KeyError:
        return

    width = int(yoga_node.get_computed_width())
    height = int(yoga_node.get_computed_height())

    # Get border color
    border_color = node.style.get(
        "borderColor",
        node.style.get(
            "borderTopColor",
            node.style.get("borderBottomColor", None),
        ),
    )

    # Get dim setting
    dim_border = node.style.get("borderDimColor", False)

    def colorize_border(s: str) -> str:
        result = s
        if dim_border:
            result = f"\x1b[2m{result}\x1b[22m"
        if border_color:
            result = colorize(result, border_color, "foreground")
        return result

    # Check which borders to draw
    show_top = node.style.get("borderTop", True)
    show_bottom = node.style.get("borderBottom", True)
    show_left = node.style.get("borderLeft", True)
    show_right = node.style.get("borderRight", True)

    # Draw top border
    if show_top:
        top_line = (
            box.top_left
            + box.top * (width - 2)
            + box.top_right
        )
        output.write(x, y, colorize_border(top_line), transformers=[])

    # Draw bottom border
    if show_bottom:
        bottom_line = (
            box.bottom_left
            + box.bottom * (width - 2)
            + box.bottom_right
        )
        output.write(x, y + height - 1, colorize_border(bottom_line), transformers=[])

    # Draw side borders
    for row in range(1, height - 1):
        if show_left:
            output.write(x, y + row, colorize_border(box.left), transformers=[])
        if show_right:
            output.write(x + width - 1, y + row, colorize_border(box.right), transformers=[])


def render_node_to_screen_reader_output(
    node: DOMElement,
    *,
    parent_role: Optional[str] = None,
    skip_static_elements: bool = False,
) -> str:
    """
    Render a DOM node for screen reader output.

    Args:
        node: The DOM node to render.
        parent_role: The parent's ARIA role.
        skip_static_elements: Whether to skip static elements.

    Returns:
        The screen reader friendly output.
    """
    if skip_static_elements and node.internal_static:
        return ""

    yoga_node = node.yoga_node
    if yoga_node and yoga_node.get_display() == yoga.DISPLAY_NONE:
        return ""

    output = ""

    if node.node_name == "ink-text":
        output = squash_text_nodes(node)
    elif node.node_name in ("ink-box", "ink-root"):
        # Determine separator based on flex direction
        flex_direction = node.style.get("flexDirection", "row")
        separator = " " if flex_direction in ("row", "row-reverse") else "\n"

        # Get children, possibly reversed
        children = list(node.child_nodes)
        if flex_direction in ("row-reverse", "column-reverse"):
            children.reverse()

        # Render children
        parts = []
        for child in children:
            if isinstance(child, DOMElement):
                child_output = render_node_to_screen_reader_output(
                    child,
                    parent_role=node.internal_accessibility.role if node.internal_accessibility else None,
                    skip_static_elements=skip_static_elements,
                )
                if child_output:
                    parts.append(child_output)

        output = separator.join(parts)

    # Add accessibility info
    if node.internal_accessibility:
        role = node.internal_accessibility.role
        state = node.internal_accessibility.state

        if state:
            state_parts = [k for k, v in state.items() if v]
            if state_parts:
                output = f"({', '.join(state_parts)}) {output}"

        if role and role != parent_role:
            output = f"{role}: {output}"

    return output
