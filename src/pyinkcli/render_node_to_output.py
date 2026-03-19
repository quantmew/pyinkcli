"""Compatibility wrapper for `pyinkcli.packages.ink.render_node_to_output`."""

from pyinkcli.packages.ink.render_node_to_output import (
    OutputTransformer,
    applyPaddingToText,
    indentString,
    renderNodeToOutput,
    renderNodeToScreenReaderOutput,
)

render_node_to_output = renderNodeToOutput
render_node_to_screen_reader_output = renderNodeToScreenReaderOutput

__all__ = [
    "OutputTransformer",
    "applyPaddingToText",
    "indentString",
    "renderNodeToOutput",
    "renderNodeToScreenReaderOutput",
]
