"""
DOM structure for pyinkcli.

Represents the virtual DOM nodes used by the renderer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Literal, Optional, Union

if TYPE_CHECKING:
    from pyinkcli._yoga import LayoutNode as YogaNode

    from pyinkcli.styles import Styles

# Node name types
ElementName = Literal["ink-root", "ink-box", "ink-text", "ink-virtual-text"]
ElementNames = ElementName
TextName = Literal["#text"]
NodeName = Union[ElementName, TextName]
NodeNames = NodeName
DOMNodeAttribute = Union[bool, str, int, float]

# Output transformer type
OutputTransformer = Callable[[str, int], str]


@dataclass
class AccessibilityInfo:
    """Accessibility information for screen readers."""

    role: Optional[str] = None
    state: Optional[dict[str, bool]] = None


@dataclass
class DOMElement:
    """Represents an element node in the DOM tree."""

    node_name: ElementName
    style: Styles = field(default_factory=dict)
    attributes: dict[str, Any] = field(default_factory=dict)
    child_nodes: list[DOMNode] = field(default_factory=list)
    parent_node: Optional[DOMElement] = None
    yoga_node: Optional[YogaNode] = None

    # Internal properties
    internal_transform: Optional[OutputTransformer] = None
    internal_static: bool = False
    internal_key: Optional[str] = None
    internal_accessibility: AccessibilityInfo = field(
        default_factory=AccessibilityInfo
    )

    # Root node callbacks
    is_static_dirty: bool = False
    static_node: Optional[DOMElement] = None
    on_compute_layout: Optional[Callable[[], None]] = None
    on_render: Optional[Callable[[], None]] = None
    on_immediate_render: Optional[Callable[[], None]] = None
    internal_layout_listeners: set[Callable[[], None]] = field(default_factory=set)


@dataclass
class TextNode:
    """Represents a text node in the DOM tree."""

    node_name: TextName = "#text"
    node_value: str = ""
    style: Styles = field(default_factory=dict)
    parent_node: Optional[DOMElement] = None
    yoga_node: Optional[YogaNode] = None


# Union type for all DOM nodes
DOMNode = Union[DOMElement, TextNode]


def _find_child_index(parent: DOMElement, child: DOMNode) -> int:
    """Find a child index by identity, not dataclass equality."""
    for index, current_child in enumerate(parent.child_nodes):
        if current_child is child:
            return index
    return -1


def createNode(node_name: ElementName) -> DOMElement:
    """
    Create a new DOM element node.

    Args:
        node_name: The type of element to create.

    Returns:
        A new DOMElement instance.
    """
    from pyinkcli._yoga import Node

    node = DOMElement(
        node_name=node_name,
        style={},
        attributes={},
        child_nodes=[],
        parent_node=None,
        yoga_node=None if node_name == "ink-virtual-text" else Node.create(),
    )

    # Set up measure function for text nodes
    if node_name == "ink-text" and node.yoga_node:
        node.yoga_node.set_measure_func(lambda w, h: _measure_text_node(node, w))

    return node


def createTextNode(text: str) -> TextNode:
    """
    Create a new text node.

    Args:
        text: The text content.

    Returns:
        A new TextNode instance.
    """
    node = TextNode(
        node_name="#text",
        node_value=text,
        style={},
        parent_node=None,
        yoga_node=None,
    )
    setTextNodeValue(node, text)
    return node


def appendChildNode(parent: DOMElement, child: DOMNode) -> None:
    """
    Append a child node to a parent element.

    Args:
        parent: The parent element.
        child: The child node to append.
    """
    if child.parent_node is not None:
        removeChildNode(child.parent_node, child)

    child.parent_node = parent
    parent.child_nodes.append(child)

    if child.yoga_node is not None and parent.yoga_node is not None:
        parent.yoga_node.insert_child(
            child.yoga_node, parent.yoga_node.get_child_count()
        )

    if parent.node_name in ("ink-text", "ink-virtual-text"):
        _mark_node_as_dirty(parent)


def insertBeforeNode(
    parent: DOMElement, new_child: DOMNode, before_child: DOMNode
) -> None:
    """
    Insert a child node before another child.

    Args:
        parent: The parent element.
        new_child: The new child to insert.
        before_child: The existing child to insert before.
    """
    if new_child.parent_node is not None:
        removeChildNode(new_child.parent_node, new_child)

    new_child.parent_node = parent

    index = _find_child_index(parent, before_child)

    if index >= 0:
        parent.child_nodes.insert(index, new_child)
        if new_child.yoga_node is not None and parent.yoga_node is not None:
            parent.yoga_node.insert_child(new_child.yoga_node, index)
    else:
        parent.child_nodes.append(new_child)
        if new_child.yoga_node is not None and parent.yoga_node is not None:
            parent.yoga_node.insert_child(
                new_child.yoga_node, parent.yoga_node.get_child_count()
            )

    if parent.node_name in ("ink-text", "ink-virtual-text"):
        _mark_node_as_dirty(parent)


def removeChildNode(parent: DOMElement, child: DOMNode) -> None:
    """
    Remove a child node from a parent element.

    Args:
        parent: The parent element.
        child: The child node to remove.
    """
    if child.yoga_node is not None and child.parent_node is not None:
        if child.parent_node.yoga_node is not None:
            child.parent_node.yoga_node.remove_child(child.yoga_node)

    child.parent_node = None

    index = _find_child_index(parent, child)
    if index >= 0:
        parent.child_nodes.pop(index)

    if parent.node_name in ("ink-text", "ink-virtual-text"):
        _mark_node_as_dirty(parent)


def setAttribute(node: DOMElement, key: str, value: Any) -> None:
    """
    Set an attribute on an element.

    Args:
        node: The element to modify.
        key: The attribute name.
        value: The attribute value.
    """
    if key == "internal_accessibility":
        node.internal_accessibility = value
        return
    node.attributes[key] = value


def setStyle(node: DOMNode, style: Optional[Styles]) -> None:
    """
    Set the style on a node.

    Args:
        node: The node to modify.
        style: The style dictionary.
    """
    node.style = style if style is not None else {}


def setTextNodeValue(node: TextNode, text: str) -> None:
    """
    Set the value of a text node.

    Args:
        node: The text node.
        text: The new text value.
    """
    if not isinstance(text, str):
        text = str(text)
    node.node_value = text
    _mark_node_as_dirty(node)


def addLayoutListener(
    root_node: DOMElement, listener: Callable[[], None]
) -> Callable[[], None]:
    """
    Add a layout listener to a root node.

    Args:
        root_node: The root node.
        listener: The listener function.

    Returns:
        A function to remove the listener.
    """
    if root_node.node_name != "ink-root":
        return lambda: None

    root_node.internal_layout_listeners.add(listener)
    return lambda: root_node.internal_layout_listeners.discard(listener)


def emitLayoutListeners(root_node: DOMElement) -> None:
    """
    Emit layout events to all listeners.

    Args:
        root_node: The root node.
    """
    if root_node.node_name != "ink-root" or not root_node.internal_layout_listeners:
        return

    for listener in root_node.internal_layout_listeners:
        listener()


add_layout_listener = addLayoutListener
emit_layout_listeners = emitLayoutListeners


def squashTextNodes(node: DOMElement) -> str:
    """
    Combine all text content from child nodes.

    Args:
        node: The element to squash.

    Returns:
        Combined text content.
    """
    from pyinkcli.sanitize_ansi import sanitizeAnsi

    text = ""
    for index, child in enumerate(node.child_nodes):
        node_text = ""
        if isinstance(child, TextNode):
            node_text = child.node_value
        elif isinstance(child, DOMElement) and child.node_name in (
            "ink-text",
            "ink-virtual-text",
        ):
            node_text = squashTextNodes(child)
            if node_text and callable(child.internal_transform):
                node_text = child.internal_transform(node_text, index)

        text += node_text

    return sanitizeAnsi(text)


def _measure_text_node(
    node: DOMNode, width: float
) -> tuple[float, float]:
    """
    Measure the dimensions of a text node.

    Args:
        node: The node to measure.
        width: Available width.

    Returns:
        Tuple of (width, height).
    """
    from pyinkcli.measure_text import measureText
    from pyinkcli.wrap_text import wrapText
    import math

    text = (
        node.node_value
        if isinstance(node, TextNode)
        else squashTextNodes(node) if isinstance(node, DOMElement) else ""
    )

    dimensions = measureText(text)

    # Text fits into container, no need to wrap
    if dimensions[0] <= width or math.isnan(width):
        return dimensions

    # Handle shrinking case
    if dimensions[0] >= 1 and 0 < width < 1:
        return dimensions

    text_wrap = node.style.get("textWrap", "wrap") if node.style else "wrap"
    wrapped_text = wrapText(text, int(width), text_wrap)

    return measureText(wrapped_text)


def _find_closest_yoga_node(node: Optional[DOMNode]) -> Optional[yoga.Node]:
    """Find the closest ancestor with a Yoga node."""
    if node is None or node.parent_node is None:
        return None
    return node.yoga_node or _find_closest_yoga_node(node.parent_node)


def _mark_node_as_dirty(node: Optional[DOMNode]) -> None:
    """Mark the closest Yoga node as dirty for re-measurement."""
    yoga_node = _find_closest_yoga_node(node)
    if yoga_node is not None:
        yoga_node.mark_dirty()


__all__ = [
    "DOMElement",
    "TextNode",
    "DOMNode",
    "DOMNodeAttribute",
    "ElementNames",
    "NodeNames",
    "createNode",
    "appendChildNode",
    "insertBeforeNode",
    "removeChildNode",
    "setAttribute",
    "setStyle",
    "createTextNode",
    "setTextNodeValue",
    "addLayoutListener",
    "emitLayoutListeners",
    "squashTextNodes",
]
