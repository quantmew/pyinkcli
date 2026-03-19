"""
Render to string functionality for pyinkcli.

This module provides the render_to_string function for rendering
Ink components to strings without terminal interaction.

Note: Due to Yoga layout limitations, render_to_string uses a fixed height
buffer and trims empty lines. For complex layouts, consider using render()
with actual terminal dimensions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from pyinkcli.packages.ink.dom import DOMElement, createNode
from pyinkcli.packages.ink.output import Output
from pyinkcli.packages.ink.render_node_to_output import renderNodeToOutput
from pyinkcli.packages.react_reconciler.ReactFiberReconciler import createReconciler
from pyinkcli.hooks._runtime import _clear_hook_state

if TYPE_CHECKING:
    from pyinkcli.component import RenderableNode


def create_root_node(columns: int, rows: int) -> DOMElement:
    """Create a root DOM element for rendering."""
    root = createNode("ink-root")
    if root.yogaNode is not None:
        root.yogaNode.set_width(columns)
        root.yogaNode.set_height(rows)
    return root


def renderToString(
    vnode: "RenderableNode",
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
        >>> from pyinkcli import renderToString, Box, Text
        >>> output = renderToString(
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

    try:
        # Create reconciler and update container
        reconciler = createReconciler(root_node)
        container = reconciler.create_container(root_node)
        reconciler.submit_container(vnode, container)

        # Get computed dimensions from the laid-out root
        yoga_node = root_node.yogaNode
        if yoga_node is None:
            return ""

        width = int(yoga_node.get_computed_width())
        height = int(yoga_node.get_computed_height())

        # Render to output
        output = Output(width, height)
        renderNodeToOutput(root_node, output)

        # Get string from output and trim trailing empty lines
        result, _ = output.get()

        # Trim trailing empty lines
        lines = result.split('\n')
        while lines and lines[-1].strip() == '':
            lines.pop()

        return '\n'.join(lines)
    finally:
        yoga_node = root_node.yogaNode
        if yoga_node is not None:
            yoga_node.free()
        _clear_hook_state()
