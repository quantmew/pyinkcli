"""
DOM structure for pyinkcli.

Represents the virtual DOM nodes used by the renderer.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal, TypedDict, Union

if TYPE_CHECKING:
    from pyinkcli._yoga import LayoutNode as YogaNode
    from pyinkcli.packages.ink.styles import Styles

# Node name types
ElementName = Literal["ink-root", "ink-box", "ink-text", "ink-virtual-text"]
ElementNames = ElementName
TextName = Literal["#text"]
NodeName = Union[ElementName, TextName]
NodeNames = NodeName
DOMNodeAttribute = Union[bool, str, int, float]

# Output transformer type
OutputTransformer = Callable[[str, int], str]


class AccessibilityInfo(TypedDict, total=False):
    role: str | None
    state: dict[str, bool]


class DOMElement:
    """Represents an element node in the DOM tree."""

    def __init__(
        self,
        nodeName: ElementName,
        *,
        style: Styles | None = None,
        attributes: dict[str, Any] | None = None,
        childNodes: list[DOMNode] | None = None,
        parentNode: DOMElement | None = None,
        yogaNode: YogaNode | None = None,
        internal_ref: Any = None,
        internal_transform: OutputTransformer | None = None,
        internal_static: bool = False,
        key: str | None = None,
        internal_accessibility: AccessibilityInfo | None = None,
        isStaticDirty: bool = False,
        staticNode: DOMElement | None = None,
        onComputeLayout: Callable[[], None] | None = None,
        onRender: Callable[[], None] | None = None,
        onImmediateRender: Callable[[], None] | None = None,
        internal_layoutListeners: set[Callable[[], None]] | None = None,
    ) -> None:
        self.nodeName = nodeName
        self.style = style or {}
        self.attributes = attributes or {}
        self.childNodes = childNodes or []
        self.parentNode = parentNode
        self.yogaNode = yogaNode
        self.internal_ref = internal_ref
        self.internal_transform = internal_transform
        self.internal_static = internal_static
        self.key = key
        self.internal_accessibility = internal_accessibility or {}
        self.isStaticDirty = isStaticDirty
        self.staticNode = staticNode
        self.onComputeLayout = onComputeLayout
        self.onRender = onRender
        self.onImmediateRender = onImmediateRender
        self.internal_layoutListeners = internal_layoutListeners or set()


class TextNode:
    """Represents a text node in the DOM tree."""

    def __init__(
        self,
        *,
        nodeName: TextName = "#text",
        nodeValue: str = "",
        style: Styles | None = None,
        parentNode: DOMElement | None = None,
        yogaNode: YogaNode | None = None,
    ) -> None:
        self.nodeName = nodeName
        self.nodeValue = nodeValue
        self.style = style or {}
        self.parentNode = parentNode
        self.yogaNode = yogaNode


# Union type for all DOM nodes
DOMNode = Union[DOMElement, TextNode]


def _find_child_index(node: DOMElement, childNode: DOMNode) -> int:
    """Find a child index by identity, not dataclass equality."""
    for index, currentChild in enumerate(node.childNodes):
        if currentChild is childNode:
            return index
    return -1


def createNode(nodeName: ElementName) -> DOMElement:
    """
    Create a new DOM element node.

    Args:
        nodeName: The type of element to create.

    Returns:
        A new DOMElement instance.
    """
    from pyinkcli._yoga import Node

    node = DOMElement(
        nodeName=nodeName,
        style={},
        attributes={},
        childNodes=[],
        parentNode=None,
        yogaNode=None if nodeName == "ink-virtual-text" else Node.create(),
    )

    # Set up measure function for text nodes
    if nodeName == "ink-text" and node.yogaNode:
        node.yogaNode.set_measure_func(lambda w, h: _measure_text_node(node, w))

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
        nodeName="#text",
        nodeValue=text,
        style={},
        parentNode=None,
        yogaNode=None,
    )
    setTextNodeValue(node, text)
    return node


def appendChildNode(node: DOMElement, childNode: DOMNode) -> None:
    """
    Append a child node to a parent element.

    Args:
        node: The parent element.
        childNode: The child node to append.
    """
    if childNode.parentNode is not None:
        removeChildNode(childNode.parentNode, childNode)

    childNode.parentNode = node
    node.childNodes.append(childNode)

    if childNode.yogaNode is not None and node.yogaNode is not None:
        node.yogaNode.insert_child(
            childNode.yogaNode, node.yogaNode.get_child_count()
        )

    if node.nodeName in ("ink-text", "ink-virtual-text"):
        _mark_node_as_dirty(node)


def insertBeforeNode(
    node: DOMElement,
    newChildNode: DOMNode,
    beforeChildNode: DOMNode,
) -> None:
    """
    Insert a child node before another child.

    Args:
        node: The parent element.
        newChildNode: The new child to insert.
        beforeChildNode: The existing child to insert before.
    """
    if newChildNode.parentNode is not None:
        removeChildNode(newChildNode.parentNode, newChildNode)

    newChildNode.parentNode = node

    index = _find_child_index(node, beforeChildNode)

    if index >= 0:
        node.childNodes.insert(index, newChildNode)
        if newChildNode.yogaNode is not None and node.yogaNode is not None:
            node.yogaNode.insert_child(newChildNode.yogaNode, index)
    else:
        node.childNodes.append(newChildNode)
        if newChildNode.yogaNode is not None and node.yogaNode is not None:
            node.yogaNode.insert_child(
                newChildNode.yogaNode, node.yogaNode.get_child_count()
            )

    if node.nodeName in ("ink-text", "ink-virtual-text"):
        _mark_node_as_dirty(node)


def removeChildNode(node: DOMElement, removeNode: DOMNode) -> None:
    """
    Remove a child node from a parent element.

    Args:
        node: The parent element.
        removeNode: The child node to remove.
    """
    if (
        removeNode.yogaNode is not None
        and removeNode.parentNode is not None
        and removeNode.parentNode.yogaNode is not None
    ):
        removeNode.parentNode.yogaNode.remove_child(removeNode.yogaNode)

    removeNode.parentNode = None

    index = _find_child_index(node, removeNode)
    if index >= 0:
        node.childNodes.pop(index)

    if node.nodeName in ("ink-text", "ink-virtual-text"):
        _mark_node_as_dirty(node)


def setAttribute(node: DOMElement, key: str, value: DOMNodeAttribute | Any) -> None:
    """
    Set an attribute on an element.

    Args:
        node: The element to modify.
        key: The attribute name.
        value: The attribute value.
    """
    if key == "internal_accessibility":
        node.internal_accessibility = value or {}
        return
    node.attributes[key] = value


def setStyle(node: DOMNode, style: Styles | None) -> None:
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
    node.nodeValue = text
    _mark_node_as_dirty(node)


def addLayoutListener(
    rootNode: DOMElement, listener: Callable[[], None]
) -> Callable[[], None]:
    """
    Add a layout listener to a root node.

    Args:
        rootNode: The root node.
        listener: The listener function.

    Returns:
        A function to remove the listener.
    """
    if rootNode.nodeName != "ink-root":
        return lambda: None

    rootNode.internal_layoutListeners.add(listener)
    return lambda: rootNode.internal_layoutListeners.discard(listener)


def emitLayoutListeners(rootNode: DOMElement) -> None:
    """
    Emit layout events to all listeners.

    Args:
        rootNode: The root node.
    """
    if rootNode.nodeName != "ink-root" or not rootNode.internal_layoutListeners:
        return

    for listener in rootNode.internal_layoutListeners:
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
    for index, child in enumerate(node.childNodes):
        nodeText = ""
        if isinstance(child, TextNode):
            nodeText = child.nodeValue
        elif isinstance(child, DOMElement) and child.nodeName in (
            "ink-text",
            "ink-virtual-text",
        ):
            nodeText = squashTextNodes(child)
            if nodeText and callable(child.internal_transform):
                nodeText = child.internal_transform(nodeText, index)

        text += nodeText

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
    import math

    from pyinkcli.measure_text import measureText
    from pyinkcli.wrap_text import wrapText

    text = (
        node.nodeValue
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

    textWrap = node.style.get("textWrap", "wrap") if node.style else "wrap"
    wrappedText = wrapText(text, int(width), textWrap)

    return measureText(wrappedText)


def _find_closest_yoga_node(node: DOMNode | None) -> YogaNode | None:
    """Find the closest ancestor with a Yoga node."""
    if node is None or node.parentNode is None:
        return None
    return node.yogaNode or _find_closest_yoga_node(node.parentNode)


def _mark_node_as_dirty(node: DOMNode | None) -> None:
    """Mark the closest Yoga node as dirty for re-measurement."""
    yogaNode = _find_closest_yoga_node(node)
    if yogaNode is not None:
        yogaNode.mark_dirty()


def cloneNodeTree(node: DOMNode) -> DOMNode:
    """Deep-clone a DOM tree for detached work."""
    if isinstance(node, TextNode):
        cloned_text = createTextNode(node.nodeValue)
        cloned_text.style = dict(node.style)
        return cloned_text

    cloned = createNode(node.nodeName)
    cloned.style = dict(node.style)
    cloned.attributes = dict(node.attributes)
    cloned.internal_ref = node.internal_ref
    cloned.internal_transform = node.internal_transform
    cloned.internal_static = node.internal_static
    cloned.key = node.key
    cloned.internal_accessibility = dict(node.internal_accessibility)
    cloned.isStaticDirty = node.isStaticDirty

    for child in node.childNodes:
        appendChildNode(cloned, cloneNodeTree(child))

    if node.staticNode is not None:
        for child, cloned_child in zip(node.childNodes, cloned.childNodes):
            if child is node.staticNode and isinstance(cloned_child, DOMElement):
                cloned.staticNode = cloned_child
                break

    return cloned


def adoptNodeTree(target: DOMElement, source: DOMElement) -> None:
    """Adopt a detached work tree into the live root."""
    while target.childNodes:
        removeChildNode(target, target.childNodes[0])

    while source.childNodes:
        appendChildNode(target, source.childNodes[0])

    target.style = dict(source.style)
    target.attributes = dict(source.attributes)
    target.internal_ref = source.internal_ref
    target.internal_transform = source.internal_transform
    target.internal_static = source.internal_static
    target.key = source.key
    target.internal_accessibility = dict(source.internal_accessibility)
    target.isStaticDirty = source.isStaticDirty
    target.staticNode = source.staticNode


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
    "cloneNodeTree",
    "adoptNodeTree",
    "squashTextNodes",
]
