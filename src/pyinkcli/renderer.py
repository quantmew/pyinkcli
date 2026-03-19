"""
Renderer for pyinkcli.

Coordinates the rendering of the DOM tree to terminal output.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pyinkcli.output import Output
from pyinkcli.render_node_to_output import (
    renderNodeToOutput,
    renderNodeToScreenReaderOutput,
)

if TYPE_CHECKING:
    from pyinkcli.dom import DOMElement


@dataclass
class RenderResult:
    """Result of rendering the DOM tree."""

    output: str
    output_height: int
    static_output: str


def render(node: DOMElement, is_screen_reader_enabled: bool = False) -> RenderResult:
    """
    Render the DOM tree to terminal output.

    Args:
        node: The root DOM node.
        is_screen_reader_enabled: Whether screen reader mode is enabled.

    Returns:
        RenderResult with output, height, and static output.
    """
    if node.yoga_node is None:
        return RenderResult(output="", output_height=0, static_output="")

    if is_screen_reader_enabled:
        return _render_screen_reader(node)

    return _render_normal(node)


def _render_normal(node: DOMElement) -> RenderResult:
    """Render for normal terminal output."""
    yoga_node = node.yoga_node

    # Create main output buffer
    main_output = Output(
        width=int(yoga_node.get_computed_width()),
        height=int(yoga_node.get_computed_height()),
    )

    # Render main content
    renderNodeToOutput(node, main_output, skip_static_elements=True)

    # Render static content if present
    static_output_str = ""
    if node.static_node and node.static_node.yoga_node:
        static_output = Output(
            width=int(node.static_node.yoga_node.get_computed_width()),
            height=int(node.static_node.yoga_node.get_computed_height()),
        )
        renderNodeToOutput(node.static_node, static_output, skip_static_elements=False)
        static_str, _ = static_output.get()
        static_output_str = static_str + "\n" if static_str else ""

    # Get final output
    output_str, height = main_output.get()

    return RenderResult(
        output=output_str,
        output_height=height,
        static_output=static_output_str,
    )


def _render_screen_reader(node: DOMElement) -> RenderResult:
    """Render for screen reader output."""
    output = renderNodeToScreenReaderOutput(node, skip_static_elements=True)
    output_height = output.count("\n") + 1 if output else 0

    static_output = ""
    if node.static_node:
        static_output = renderNodeToScreenReaderOutput(
            node.static_node, skip_static_elements=False
        )
        if static_output:
            static_output += "\n"

    return RenderResult(
        output=output,
        output_height=output_height,
        static_output=static_output,
    )
