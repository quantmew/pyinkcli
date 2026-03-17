"""
Render to string functionality for ink-python.

This module provides the render_to_string function for rendering
Ink components to strings without terminal interaction.

Note: Due to Yoga layout limitations, render_to_string uses a fixed height
buffer and trims empty lines. For complex layouts, consider using render()
with actual terminal dimensions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ink_python.component import VNode
from ink_python.output import Output
from ink_python.render_node_to_output import render_node_to_output
from ink_python.yoga_compat import Node, DIRECTION_LTR, UNDEFINED
from ink_python.reconciler import create_reconciler

if TYPE_CHECKING:
    from ink_python.dom import DOMElement


def create_root_node(columns: int, rows: int) -> "DOMElement":
    """Create a root DOM element for rendering."""
    from ink_python.dom import create_node

    root = create_node("ink-root")
    root.yoga_node = Node.create()
    # Set both width and height - Yoga requires explicit dimensions
    root.yoga_node.set_width(columns)
    root.yoga_node.set_height(rows)
    return root


def render_to_string(
    vnode: VNode,
    columns: Optional[int] = None,
    rows: Optional[int] = None,
) -> str:
    """
    Render a vnode to a string synchronously.

    Unlike render(), this function does not write to stdout, does not set up
    any terminal event listeners, and returns the rendered output as a string.

    Note: Due to Yoga layout limitations, this function uses a fixed height
    buffer. If content exceeds the height, it will be clipped. Set rows
    sufficiently large to accommodate your content.

    Args:
        vnode: The virtual node to render.
        columns: Width of the virtual terminal in columns. Defaults to 80.
        rows: Height of the virtual terminal in rows. Defaults to 25.

    Returns:
        The rendered output as a string.

    Example:
        >>> from ink_python import render_to_string, Box, Text
        >>> output = render_to_string(
        ...     Box(
        ...         Text("Hello World")
        ...     ),
        ...     columns=40,
        ...     rows=10
        ... )
        >>> print(output)
    """
    columns = columns if columns is not None else 80
    rows = rows if rows is not None else 25

    # Create a root node with explicit dimensions
    root_node = create_root_node(columns, rows)

    # Create reconciler and update container
    reconciler = create_reconciler(root_node)
    container = reconciler.create_container(root_node)
    reconciler.update_container(vnode, container)

    # Get computed dimensions from the laid-out root
    yoga_node = root_node.yoga_node
    if yoga_node is None:
        return ""

    width = int(yoga_node.get_computed_width())
    height = int(yoga_node.get_computed_height())

    # Render to output
    output = Output(width, height)
    render_node_to_output(root_node, output)

    # Free yoga node
    yoga_node.free()

    # Get string from output and trim trailing empty lines
    result, _ = output.get()

    # Trim trailing empty lines
    lines = result.split('\n')
    while lines and lines[-1].strip() == '':
        lines.pop()

    return '\n'.join(lines)


# CamelCase alias for JavaScript compatibility
renderToString = render_to_string
