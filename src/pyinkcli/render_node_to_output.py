"""
Render nodes to output for pyinkcli.

Converts DOM nodes to terminal output.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Callable, Optional

from pyinkcli import _yoga as yoga
from pyinkcli.get_max_width import getMaxWidth

from pyinkcli.dom import DOMElement, TextNode, DOMNode, squashTextNodes
from pyinkcli.wrap_text import wrapText
from pyinkcli.utils.string_width import widest_line
from pyinkcli.output import Output
from pyinkcli.render_background import renderBackground
from pyinkcli.render_border import renderBorder

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
        state_labels.extend(key for key, value in state.items() if value)
        if state_labels:
            output = f"({', '.join(state_labels)}) {output}"

    if role and role != parent_role:
        output = f"{role}: {output}"

    return output


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
            current_width = widest_line(text)
            max_width = _clamped_max_width(yoga_node)

            if current_width > max_width:
                text_wrap = node.style.get("textWrap", "wrap")
                text = wrapText(text, max_width, text_wrap)

            text = applyPaddingToText(node, text)
            output.write(x, y, text, transformers=new_transformers)
        return

    clipped = False

    if node.node_name == "ink-box":
        renderBackground(x, y, node, output)
        renderBorder(x, y, node, output)

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
            clipped = True

    if node.node_name in ("ink-root", "ink-box"):
        for child in node.child_nodes:
            if isinstance(child, DOMElement):
                renderNodeToOutput(
                    child,
                    output,
                    offset_x=x,
                    offset_y=y,
                    transformers=new_transformers,
                    skip_static_elements=skip_static_elements,
                )

        if clipped:
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
        output = squashTextNodes(node)
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
