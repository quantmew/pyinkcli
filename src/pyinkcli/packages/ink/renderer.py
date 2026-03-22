"""Render the current DOM tree into terminal output."""

from __future__ import annotations

from dataclasses import dataclass

from pyinkcli.packages.ink.layout_utils import safe_layout_int
from pyinkcli.packages.ink.output import Output
from pyinkcli.packages.ink.render_node_to_output import (
    renderNodeToOutput,
    renderNodeToScreenReaderOutput,
)


@dataclass
class RenderResult:
    output: str
    outputHeight: int
    staticOutput: str = ""


def render(root_node, is_screen_reader_enabled: bool = False) -> RenderResult:
    if is_screen_reader_enabled:
        output = renderNodeToScreenReaderOutput(root_node, {"skipStaticElements": True})
        height = output.count("\n") + 1 if output else 0
        static_output = renderNodeToScreenReaderOutput(root_node, {"onlyStaticElements": True})
        return RenderResult(output=output, outputHeight=height, staticOutput=static_output)

    yoga_node = getattr(root_node, "yogaNode", None)
    width = safe_layout_int(yoga_node.get_computed_width()) if yoga_node is not None else 0
    height = safe_layout_int(yoga_node.get_computed_height()) if yoga_node is not None else 0
    output_buffer = Output({"width": max(width, 1), "height": max(height, 1)})
    renderNodeToOutput(root_node, output_buffer, {"skipStaticElements": True})
    main = output_buffer.get().output
    static_buffer = Output({"width": max(width, 1), "height": max(height, 1)})
    renderNodeToOutput(root_node, static_buffer, {"onlyStaticElements": True})
    static_output = static_buffer.get().output
    return RenderResult(output=main, outputHeight=max(1, main.count("\n") + 1 if main else 0), staticOutput=static_output)
