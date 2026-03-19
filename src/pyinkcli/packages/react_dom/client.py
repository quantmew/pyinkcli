"""Terminal renderer entrypoint analogous to the react-dom client surface."""

from __future__ import annotations

from typing import Optional

from pyinkcli.packages.ink.output import Output
from pyinkcli.packages.ink.render_background import renderBackground
from pyinkcli.packages.ink.render_border import renderBorder
from pyinkcli.packages.ink.render_node_to_output import (
    OutputTransformer,
    applyPaddingToText,
    indentString,
    renderNodeToOutput,
    renderNodeToScreenReaderOutput,
)
from pyinkcli.packages.ink.renderer import RenderResult, render as renderHostTree
from pyinkcli.packages.react_dom.host import DOMElement, createNode


def createRootNode(
    columns: Optional[int] = None,
    rows: Optional[int] = None,
) -> DOMElement:
    """Create a terminal root host node for the renderer."""
    root = createNode("ink-root")
    if root.yoga_node is not None:
        if columns is not None:
            root.yoga_node.set_width(columns)
        if rows is not None:
            root.yoga_node.set_height(rows)
    return root


def render(
    node: DOMElement,
    is_screen_reader_enabled: bool = False,
) -> RenderResult:
    """Render a terminal host tree through the client renderer entrypoint."""
    return renderHostTree(node, is_screen_reader_enabled=is_screen_reader_enabled)


__all__ = [
    "Output",
    "OutputTransformer",
    "RenderResult",
    "applyPaddingToText",
    "createRootNode",
    "indentString",
    "render",
    "renderBackground",
    "renderBorder",
    "renderNodeToOutput",
    "renderNodeToScreenReaderOutput",
]
