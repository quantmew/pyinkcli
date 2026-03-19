"""Render coordinator for the internal Ink host view package."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyinkcli.packages.ink.output import Output
from pyinkcli.packages.ink.render_node_to_output import (
    renderNodeToOutput,
    renderNodeToScreenReaderOutput,
)

if TYPE_CHECKING:
    from pyinkcli.packages.ink.dom import DOMElement


class RenderResult:
    def __init__(self, output: str, outputHeight: int, staticOutput: str) -> None:
        self.output = output
        self.outputHeight = outputHeight
        self.staticOutput = staticOutput


def render(node: DOMElement, isScreenReaderEnabled: bool = False) -> RenderResult:
    if node.yogaNode:
        if isScreenReaderEnabled:
            output = renderNodeToScreenReaderOutput(node, {"skipStaticElements": True})
            outputHeight = 0 if output == "" else len(output.split("\n"))

            staticOutput = ""
            if node.staticNode:
                staticOutput = renderNodeToScreenReaderOutput(
                    node.staticNode, {"skipStaticElements": False}
                )

            return RenderResult(
                output=output,
                outputHeight=outputHeight,
                staticOutput=f"{staticOutput}\n" if staticOutput else "",
            )

        mainOutput = Output(
            {
                "width": int(node.yogaNode.get_computed_width()),
                "height": int(node.yogaNode.get_computed_height()),
            }
        )

        renderNodeToOutput(node, mainOutput, {"skipStaticElements": True})

        staticOutputBuffer: Output | None = None
        if node.staticNode and node.staticNode.yogaNode:
            staticOutputBuffer = Output(
                {
                    "width": int(node.staticNode.yogaNode.get_computed_width()),
                    "height": int(node.staticNode.yogaNode.get_computed_height()),
                }
            )
            renderNodeToOutput(
                node.staticNode, staticOutputBuffer, {"skipStaticElements": False}
            )

        outputResult = mainOutput.get()

        static_output = ""
        if staticOutputBuffer:
            static_output = f"{staticOutputBuffer.get().output}\n"

        return RenderResult(
            output=outputResult.output,
            outputHeight=outputResult.height,
            staticOutput=static_output,
        )

    return RenderResult(output="", outputHeight=0, staticOutput="")
