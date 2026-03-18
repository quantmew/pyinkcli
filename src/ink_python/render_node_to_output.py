"""
Render nodes to output for ink-python.

Converts DOM nodes to terminal output.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Callable, Optional

from ink_python import _yoga as yoga
from ink_python.get_max_width import getMaxWidth

from ink_python.dom import DOMElement, TextNode, DOMNode, squashTextNodes
from ink_python.wrap_text import wrapText
from ink_python.sanitize_ansi import sanitizeAnsi
from ink_python.utils.string_width import widest_line
from ink_python.output import Output
from ink_python.render_background import renderBackground
from ink_python.render_border import renderBorder

if TYPE_CHECKING:
    pass

# Output transformer type
OutputTransformer = Callable[[str, int], str]


def _format_accessibility_output(
    role: Optional[str],
    state: Optional[dict[str, bool]],
    output: str,
    parent_role: Optional[str],
) -> str:
    """Format screen reader output for ARIA role/state metadata."""
    if not role and not state:
        return output

    state_labels: list[str] = []
    if state:
        if role == "checkbox" and "checked" in state:
            state_labels.append("checked" if state["checked"] else "unchecked")
        else:
            state_labels.extend(key for key, value in state.items() if value)

    parts: list[str] = []
    if role and role != parent_role:
        parts.append(f"{role}:")
    parts.extend(state_labels)
    if output:
        parts.append(output)

    return " ".join(part for part in parts if part)


def applyPaddingToText(node: DOMElement, text: str) -> str:
    """Apply padding offset to text."""
    if node.child_nodes:
        first_child = node.child_nodes[0]
        if hasattr(first_child, "yoga_node") and first_child.yoga_node:
            offset_x = first_child.yoga_node.get_computed_left()
            offset_y = first_child.yoga_node.get_computed_top()
            text = "\n" * offset_y + indentString(text, offset_x)
    return text


def indentString(text: str, count: int) -> str:
    """Indent each line of text."""
    if count <= 0:
        return text
    indent = " " * count
    return "\n".join(indent + line for line in text.split("\n"))


def _clamped_max_width(yoga_node) -> int:
    """Clamp the JS-style max width helper to a non-negative integer width."""
    result = getMaxWidth(yoga_node)
    if not math.isfinite(result):
        return 0
    return max(0, int(result))


def renderNodeToOutput(
    node: DOMElement,
    output: Output,
    *,
    offset_x: int = 0,
    offset_y: int = 0,
    inherited_background: Optional[str] = None,
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
        text = squashTextNodes(node)
        if text:
            text = sanitizeAnsi(text)
            current_width = widest_line(text)
            max_width = _clamped_max_width(yoga_node)

            if current_width > max_width:
                text_wrap = node.style.get("textWrap", "wrap")
                text = wrapText(text, max_width, text_wrap)

            text = applyPaddingToText(node, text)
            text_background = node.style.get("backgroundColor") or inherited_background
            if text_background:
                from ink_python.colorize import colorize

                def bg_transform(s: str, index: int, bg: str = text_background) -> str:
                    return colorize(s, bg, "background")

                new_transformers.append(bg_transform)

            output.write(x, y, text, transformers=new_transformers)
        return

    # Handle box elements
    clip_horizontal = False
    clip_vertical = False

    next_inherited_background = inherited_background

    if node.node_name == "ink-box":
        # Render background
        renderBackground(x, y, node, output)
        next_inherited_background = node.style.get("backgroundColor") or inherited_background

        # Render border
        renderBorder(x, y, node, output)

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
                renderNodeToOutput(
                    child,
                    output,
                    offset_x=x,
                    offset_y=y,
                    inherited_background=next_inherited_background,
                    transformers=new_transformers,
                    skip_static_elements=skip_static_elements,
                )

        # Unclip if we clipped
        if clip_horizontal or clip_vertical:
            output.unclip()


def renderNodeToScreenReaderOutput(
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
        output = sanitizeAnsi(squashTextNodes(node))
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
                child_output = renderNodeToScreenReaderOutput(
                    child,
                    parent_role=node.internal_accessibility.role if node.internal_accessibility else None,
                    skip_static_elements=skip_static_elements,
                )
                if child_output:
                    parts.append(child_output)

        output = separator.join(parts)

    # Add accessibility info
    if node.internal_accessibility:
        output = _format_accessibility_output(
            node.internal_accessibility.role,
            node.internal_accessibility.state,
            output,
            parent_role,
        )

    return output


render_node_to_output = renderNodeToOutput
render_node_to_screen_reader_output = renderNodeToScreenReaderOutput

__all__ = [
    "OutputTransformer",
    "applyPaddingToText",
    "indentString",
    "renderNodeToOutput",
    "renderNodeToScreenReaderOutput",
]
