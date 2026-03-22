"""DOM tree rendering to output buffer."""

from __future__ import annotations

from typing import Callable

from pyinkcli.packages.ink.render_background import renderBackground
from pyinkcli.packages.ink.render_border import renderBorder
from pyinkcli.packages.ink.dom import DOMElement, squashTextNodes
from pyinkcli.packages.ink.layout_utils import safe_layout_int
from pyinkcli.wrap_text import wrapText
from pyinkcli.utils.string_width import widest_line

OutputTransformer = Callable[[str, int], str]


def indentString(text: str, count: int) -> str:
    prefix = " " * max(0, count)
    return "\n".join(prefix + line if line else prefix for line in text.split("\n"))


def applyPaddingToText(node: DOMElement, text: str) -> str:
    yoga_node = node.childNodes[0].yogaNode if node.childNodes else None
    if yoga_node is None:
        return text
    offset_x = safe_layout_int(yoga_node.get_computed_left())
    offset_y = safe_layout_int(yoga_node.get_computed_top())
    if offset_x is None or offset_y is None:
        return text
    return "\n" * offset_y + indentString(text, offset_x)


def renderNodeToScreenReaderOutput(node: DOMElement, options: dict | None = None) -> str:
    options = options or {}
    skip_static = bool(options.get("skipStaticElements", False))
    only_static = bool(options.get("onlyStaticElements", False))
    within_static_tree = bool(options.get("withinStaticTree", False)) or node.internal_static
    if skip_static and node.internal_static:
        return ""
    include_current = not only_static or within_static_tree or node.nodeName == "ink-root"
    output = ""
    if include_current and node.nodeName == "ink-text":
        output = squashTextNodes(node)
    elif node.nodeName in ("ink-box", "ink-root"):
        separator = " " if node.style.get("flexDirection") in ("row", "row-reverse") else "\n"
        child_nodes = list(node.childNodes)
        if node.style.get("flexDirection") in ("row-reverse", "column-reverse"):
            child_nodes.reverse()
        output = separator.join(
            filter(
                None,
                [
                    renderNodeToScreenReaderOutput(
                        child,
                        {
                            "parentRole": node.internal_accessibility.get("role"),
                            "skipStaticElements": skip_static,
                            "onlyStaticElements": only_static,
                            "withinStaticTree": within_static_tree,
                        },
                    )
                    for child in child_nodes
                    if isinstance(child, DOMElement)
                ],
            )
        )
    role = node.internal_accessibility.get("role")
    state = node.internal_accessibility.get("state") or {}
    if state:
        state_description = ", ".join(key for key, value in state.items() if value)
        if state_description:
            output = f"({state_description}) {output}"
    if role and role != options.get("parentRole"):
        output = f"{role}: {output}"
    return output


def renderNodeToOutput(node: DOMElement, output, options: dict | None = None) -> None:
    options = options or {}
    offset_x = int(options.get("offsetX", 0))
    offset_y = int(options.get("offsetY", 0))
    transformers = list(options.get("transformers", []))
    skip_static = bool(options.get("skipStaticElements", False))
    only_static = bool(options.get("onlyStaticElements", False))
    within_static_tree = bool(options.get("withinStaticTree", False)) or node.internal_static
    if skip_static and node.internal_static:
        return
    yoga_node = node.yogaNode
    if yoga_node is None:
        return
    computed_left = safe_layout_int(yoga_node.get_computed_left())
    computed_top = safe_layout_int(yoga_node.get_computed_top())
    if computed_left is None or computed_top is None:
        return
    x = offset_x + computed_left
    y = offset_y + computed_top
    new_transformers = transformers
    if callable(node.internal_transform):
        new_transformers = [node.internal_transform, *transformers]
    include_current = not only_static or within_static_tree or node.nodeName == "ink-root"

    if include_current and node.nodeName == "ink-text":
        text = squashTextNodes(node)
        if text:
            current_width = widest_line(text)
            computed_width = safe_layout_int(yoga_node.get_computed_width())
            if computed_width is None:
                return
            max_width = int(max(0, computed_width - yoga_node.get_computed_padding(0) - yoga_node.get_computed_padding(2) - yoga_node.get_computed_border(0) - yoga_node.get_computed_border(2)))
            if max_width and current_width > max_width:
                text = wrapText(text, max_width, node.style.get("textWrap", "wrap"))
            text = applyPaddingToText(node, text)
            output.write(x, y, text, {"transformers": new_transformers})
        return

    if include_current and node.nodeName == "ink-box":
        renderBackground(x, y, node, output)
        renderBorder(x, y, node, output)

    for child in node.childNodes:
        if isinstance(child, DOMElement):
            renderNodeToOutput(
                child,
                output,
                {
                    "offsetX": x,
                    "offsetY": y,
                    "transformers": new_transformers,
                    "skipStaticElements": skip_static,
                    "onlyStaticElements": only_static,
                    "withinStaticTree": within_static_tree,
                },
            )
