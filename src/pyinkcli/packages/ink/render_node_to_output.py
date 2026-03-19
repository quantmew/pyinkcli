"""Render host DOM nodes to terminal output for the internal Ink package."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Callable, Optional

from pyinkcli import _yoga as yoga
from pyinkcli.get_max_width import getMaxWidth

from pyinkcli.packages.ink.dom import DOMElement, TextNode, DOMNode, squashTextNodes
from pyinkcli.wrap_text import wrapText
from pyinkcli.utils.string_width import widest_line
from pyinkcli.packages.ink.output import Output
from pyinkcli.packages.ink.render_background import renderBackground
from pyinkcli.packages.ink.render_border import renderBorder

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
    if node.childNodes:
        firstChild = node.childNodes[0]
        if hasattr(firstChild, "yogaNode") and firstChild.yogaNode:
            offsetX = firstChild.yogaNode.get_computed_left()
            offsetY = firstChild.yogaNode.get_computed_top()
            text = "\n" * offsetY + indentString(text, offsetX)
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
    options: Optional[dict[str, object]] = None,
) -> None:
    """
    Render a DOM node to the output buffer.

    Args:
        node: The DOM node to render.
        output: The output buffer.
        options: Render options aligned with Ink's renderer surface.
    """
    options = options or {}
    offsetX = int(options.get("offsetX", 0))
    offsetY = int(options.get("offsetY", 0))
    transformers = list(options.get("transformers", []) or [])
    skipStaticElements = bool(options.get("skipStaticElements", False))

    if skipStaticElements and node.internal_static:
        return

    yogaNode = node.yogaNode
    if yogaNode is None:
        return

    if yogaNode.get_display() == yoga.DISPLAY_NONE:
        return

    x = int(offsetX + yogaNode.get_computed_left())
    y = int(offsetY + yogaNode.get_computed_top())

    newTransformers = transformers
    if node.internal_transform is not None:
        newTransformers = [node.internal_transform, *transformers]

    if node.nodeName == "ink-text":
        text = squashTextNodes(node)
        if text:
            currentWidth = widest_line(text)
            maxWidth = _clamped_max_width(yogaNode)

            if currentWidth > maxWidth:
                textWrap = node.style.get("textWrap", "wrap")
                text = wrapText(text, maxWidth, textWrap)

            text = applyPaddingToText(node, text)
            output.write(x, y, text, transformers=newTransformers)
        return

    clipped = False

    if node.nodeName == "ink-box":
        renderBackground(x, y, node, output)
        renderBorder(x, y, node, output)

        clipHorizontally = (
            node.style.get("overflowX") == "hidden"
            or node.style.get("overflow") == "hidden"
        )
        clipVertically = (
            node.style.get("overflowY") == "hidden"
            or node.style.get("overflow") == "hidden"
        )

        if clipHorizontally or clipVertically:
            x1 = (
                x + yogaNode.get_computed_border(yoga.EDGE_LEFT)
                if clipHorizontally
                else None
            )
            x2 = (
                x
                + yogaNode.get_computed_width()
                - yogaNode.get_computed_border(yoga.EDGE_RIGHT)
                if clipHorizontally
                else None
            )
            y1 = (
                y + yogaNode.get_computed_border(yoga.EDGE_TOP)
                if clipVertically
                else None
            )
            y2 = (
                y
                + yogaNode.get_computed_height()
                - yogaNode.get_computed_border(yoga.EDGE_BOTTOM)
                if clipVertically
                else None
            )

            output.clip(x1=x1, x2=x2, y1=y1, y2=y2)
            clipped = True

    if node.nodeName in ("ink-root", "ink-box"):
        for childNode in node.childNodes:
            if isinstance(childNode, DOMElement):
                renderNodeToOutput(
                    childNode,
                    output,
                    {
                        "offsetX": x,
                        "offsetY": y,
                        "transformers": newTransformers,
                        "skipStaticElements": skipStaticElements,
                    },
                )

        if clipped:
            output.unclip()


def renderNodeToScreenReaderOutput(
    node: DOMElement,
    options: Optional[dict[str, object]] = None,
) -> str:
    """
    Render a DOM node for screen reader output.

    Args:
        node: The DOM node to render.
        options: Render options aligned with Ink's renderer surface.

    Returns:
        The screen reader friendly output.
    """
    options = options or {}
    parentRole = options.get("parentRole")
    skipStaticElements = bool(options.get("skipStaticElements", False))

    if skipStaticElements and node.internal_static:
        return ""

    yogaNode = node.yogaNode
    if yogaNode and yogaNode.get_display() == yoga.DISPLAY_NONE:
        return ""

    output = ""

    if node.nodeName == "ink-text":
        output = squashTextNodes(node)
    elif node.nodeName in ("ink-box", "ink-root"):
        # Determine separator based on flex direction
        separator = (
            " "
            if node.style.get("flexDirection") in ("row", "row-reverse")
            else "\n"
        )
        childNodes = (
            list(reversed(node.childNodes))
            if node.style.get("flexDirection") in ("row-reverse", "column-reverse")
            else list(node.childNodes)
        )
        output = separator.join(
            filter(
                None,
                [
                    renderNodeToScreenReaderOutput(
                        childNode,
                        {
                            "parentRole": (
                                node.internal_accessibility.get("role")
                                if node.internal_accessibility
                                else None
                            ),
                            "skipStaticElements": skipStaticElements,
                        },
                    )
                    for childNode in childNodes
                    if isinstance(childNode, DOMElement)
                ],
            )
        )

    # Add accessibility info
    if node.internal_accessibility:
        output = _format_accessibility_output(
            node.internal_accessibility.get("role"),
            node.internal_accessibility.get("state"),
            output,
            parentRole,
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
