"""
Squash text nodes for ink-python.

Combines adjacent text nodes into a single string.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ink_python.dom import DOMElement, DOMNode, TextNode


def squash_text_nodes(node: DOMElement) -> str:
    """
    Combine all text content from child nodes into a single string.

    Args:
        node: The element to squash.

    Returns:
        Combined text content.
    """
    texts: list[str] = []

    for child in node.child_nodes:
        if child.node_name == "#text":
            # TextNode
            texts.append(child.node_value)
        elif child.node_name == "ink-virtual-text":
            # Virtual text element - recurse
            texts.append(squash_text_nodes(child))

    return "".join(texts)
