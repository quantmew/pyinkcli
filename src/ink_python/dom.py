"""
DOM structure for ink-python.

Represents the virtual DOM nodes used by the renderer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Literal, Optional, Union

if TYPE_CHECKING:
    from ink_python.yoga_compat import LayoutNode as YogaNode

    from ink_python.styles import Styles

# Node name types
ElementName = Literal["ink-root", "ink-box", "ink-text", "ink-virtual-text"]
TextName = Literal["#text"]
NodeName = Union[ElementName, TextName]

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


def create_node(node_name: ElementName) -> DOMElement:
    """
    Create a new DOM element node.

    Args:
        node_name: The type of element to create.

    Returns:
        A new DOMElement instance.
    """
    from ink_python.yoga_compat import Node

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


def create_text_node(text: str) -> TextNode:
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
    set_text_node_value(node, text)
    return node


def append_child_node(parent: DOMElement, child: DOMNode) -> None:
    """
    Append a child node to a parent element.

    Args:
        parent: The parent element.
        child: The child node to append.
    """
    if child.parent_node is not None:
        remove_child_node(child.parent_node, child)

    child.parent_node = parent
    parent.child_nodes.append(child)

    if child.yoga_node is not None and parent.yoga_node is not None:
        parent.yoga_node.insert_child(
            child.yoga_node, parent.yoga_node.get_child_count()
        )

    if parent.node_name in ("ink-text", "ink-virtual-text"):
        _mark_node_as_dirty(parent)


def insert_before_node(
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
        remove_child_node(new_child.parent_node, new_child)

    new_child.parent_node = parent

    try:
        index = parent.child_nodes.index(before_child)
    except ValueError:
        index = -1

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


def remove_child_node(parent: DOMElement, child: DOMNode) -> None:
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

    try:
        index = parent.child_nodes.index(child)
        parent.child_nodes.pop(index)
    except ValueError:
        pass

    if parent.node_name in ("ink-text", "ink-virtual-text"):
        _mark_node_as_dirty(parent)


def set_attribute(node: DOMElement, key: str, value: Any) -> None:
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


def set_style(node: DOMNode, style: Optional[Styles]) -> None:
    """
    Set the style on a node.

    Args:
        node: The node to modify.
        style: The style dictionary.
    """
    node.style = style if style is not None else {}


def set_text_node_value(node: TextNode, text: str) -> None:
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


def add_layout_listener(
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


def emit_layout_listeners(root_node: DOMElement) -> None:
    """
    Emit layout events to all listeners.

    Args:
        root_node: The root node.
    """
    if root_node.node_name != "ink-root" or not root_node.internal_layout_listeners:
        return

    for listener in root_node.internal_layout_listeners:
        listener()


def squash_text_nodes(node: DOMElement) -> str:
    """
    Combine all text content from child nodes.

    Args:
        node: The element to squash.

    Returns:
        Combined text content.
    """
    texts: list[str] = []
    for child in node.child_nodes:
        if isinstance(child, TextNode):
            texts.append(child.node_value)
        elif isinstance(child, DOMElement) and child.node_name == "ink-virtual-text":
            texts.append(squash_text_nodes(child))
    return "".join(texts)


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
    from ink_python.measure_text import measure_text
    from ink_python.wrap_text import wrap_text
    import math

    text = (
        node.node_value
        if isinstance(node, TextNode)
        else squash_text_nodes(node) if isinstance(node, DOMElement) else ""
    )

    dimensions = measure_text(text)

    # Text fits into container, no need to wrap
    if dimensions[0] <= width or math.isnan(width):
        return dimensions

    # Handle shrinking case
    if dimensions[0] >= 1 and 0 < width < 1:
        return dimensions

    text_wrap = node.style.get("textWrap", "wrap") if node.style else "wrap"
    wrapped_text = wrap_text(text, int(width), text_wrap)

    return measure_text(wrapped_text)


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
