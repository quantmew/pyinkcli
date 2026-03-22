"""DOM primitives translated from Ink's DOM layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Union

from pyinkcli import _yoga as yoga
from pyinkcli.measure_text import measureText
from pyinkcli.packages.ink.styles import Styles
from pyinkcli.sanitize_ansi import sanitizeAnsi
from pyinkcli.utils.string_width import string_width
from pyinkcli.wrap_text import wrapText

TextName = Literal["#text"]
ElementNames = Literal["ink-root", "ink-box", "ink-text", "ink-virtual-text"]
NodeNames = Literal["ink-root", "ink-box", "ink-text", "ink-virtual-text", "#text"]
DOMNodeAttribute = Union[bool, str, int, float, dict[str, Any]]


@dataclass
class DOMNode:
    nodeName: NodeNames
    parentNode: "DOMElement | None" = None
    yogaNode: yoga.LayoutNode | None = None
    internal_static: bool = False
    style: Styles = field(default_factory=dict)


@dataclass
class TextNode(DOMNode):
    nodeValue: str = ""

    def __init__(self, text: str):
        super().__init__(nodeName="#text", parentNode=None, yogaNode=None, style={})
        self.nodeValue = text


@dataclass
class DOMElement(DOMNode):
    nodeName: ElementNames
    attributes: dict[str, DOMNodeAttribute] = field(default_factory=dict)
    childNodes: list[DOMNode] = field(default_factory=list)
    internal_transform: Any = None
    internal_accessibility: dict[str, Any] = field(default_factory=dict)
    isStaticDirty: bool = False
    staticNode: "DOMElement | None" = None
    onComputeLayout: Any = None
    onRender: Any = None
    onImmediateRender: Any = None
    internal_layoutListeners: set[Any] = field(default_factory=set)
    rendered_tree: Any = None


def _measure_text_node(node: DOMNode, width: float, _height: float) -> tuple[float, float]:
    text = node.nodeValue if node.nodeName == "#text" else squashTextNodes(node)  # type: ignore[attr-defined]
    measured_width, measured_height = measureText(text)
    if measured_width <= width or width <= 0:
        return (measured_width, measured_height)
    text_wrap = getattr(node, "style", {}).get("textWrap", "wrap")
    wrapped = wrapText(text, int(width), text_wrap)
    return measureText(wrapped)


def createNode(nodeName: ElementNames) -> DOMElement:
    node = DOMElement(
        nodeName=nodeName,
        parentNode=None,
        yogaNode=None if nodeName == "ink-virtual-text" else yoga.LayoutNode.create(),
        style={},
        attributes={},
        childNodes=[],
        internal_accessibility={},
    )
    if node.nodeName == "ink-text" and node.yogaNode is not None:
        node.yogaNode.set_measure_func(lambda width, height: _measure_text_node(node, width, height))
    return node


def createTextNode(text: str) -> TextNode:
    return TextNode(text)


def _find_closest_yoga_node(node: DOMNode | None) -> yoga.LayoutNode | None:
    current = node
    while current is not None:
        if current.yogaNode is not None:
            return current.yogaNode
        current = current.parentNode
    return None


def _mark_node_as_dirty(node: DOMNode | None) -> None:
    yoga_node = _find_closest_yoga_node(node)
    if yoga_node is not None:
        yoga_node.mark_dirty()


def appendChildNode(node: DOMElement, childNode: DOMNode) -> None:
    if childNode.parentNode is not None:
        removeChildNode(childNode.parentNode, childNode)
    childNode.parentNode = node
    node.childNodes.append(childNode)
    if node.yogaNode is not None and childNode.yogaNode is not None:
        node.yogaNode.insert_child(childNode.yogaNode, node.yogaNode.get_child_count())
    if node.nodeName in ("ink-text", "ink-virtual-text"):
        _mark_node_as_dirty(node)


def insertBeforeNode(node: DOMElement, newChildNode: DOMNode, beforeChildNode: DOMNode) -> None:
    if newChildNode.parentNode is not None:
        removeChildNode(newChildNode.parentNode, newChildNode)
    newChildNode.parentNode = node
    try:
        index = node.childNodes.index(beforeChildNode)
    except ValueError:
        index = len(node.childNodes)
    node.childNodes.insert(index, newChildNode)
    if node.yogaNode is not None and newChildNode.yogaNode is not None:
        node.yogaNode.insert_child(newChildNode.yogaNode, index)
    if node.nodeName in ("ink-text", "ink-virtual-text"):
        _mark_node_as_dirty(node)


def removeChildNode(node: DOMElement, removeNode: DOMNode) -> None:
    if node.yogaNode is not None and removeNode.yogaNode is not None:
        node.yogaNode.remove_child(removeNode.yogaNode)
    if removeNode in node.childNodes:
        node.childNodes.remove(removeNode)
    removeNode.parentNode = None
    if node.nodeName in ("ink-text", "ink-virtual-text"):
        _mark_node_as_dirty(node)


def setAttribute(node: DOMElement, key: str, value: DOMNodeAttribute) -> None:
    if key == "internal_accessibility" and isinstance(value, dict):
        node.internal_accessibility = value
        return
    node.attributes[key] = value


def _apply_dimension(node: DOMElement, key: str, value: Any) -> None:
    if node.yogaNode is None:
        return
    if value is None:
        return
    if isinstance(value, str) and value.endswith("%"):
        percent = float(value[:-1])
        if key == "width":
            node.yogaNode.set_width_percent(percent)
        elif key == "height":
            node.yogaNode.set_height_percent(percent)
        return
    numeric = float(value)
    if key == "width":
        node.yogaNode.set_width(numeric)
    elif key == "height":
        node.yogaNode.set_height(numeric)


def _apply_edge_values(node: DOMElement, setter_name: str, prefix: str, all_value: Any, x_value: Any, y_value: Any) -> None:
    if node.yogaNode is None:
        return
    setter = getattr(node.yogaNode, setter_name)
    if all_value is not None:
        setter(yoga.EDGE_ALL, float(all_value))
    if x_value is not None:
        setter(yoga.EDGE_LEFT, float(x_value))
        setter(yoga.EDGE_RIGHT, float(x_value))
    if y_value is not None:
        setter(yoga.EDGE_TOP, float(y_value))
        setter(yoga.EDGE_BOTTOM, float(y_value))
    for edge_name, edge in (
        (f"{prefix}Top", yoga.EDGE_TOP),
        (f"{prefix}Bottom", yoga.EDGE_BOTTOM),
        (f"{prefix}Left", yoga.EDGE_LEFT),
        (f"{prefix}Right", yoga.EDGE_RIGHT),
    ):
        value = node.style.get(edge_name)
        if value is not None:
            setter(edge, float(value))


def _resolve_border_width(node: DOMElement, edge_key: str, enabled_key: str) -> float:
    if not node.style.get("borderStyle"):
        return 0.0
    if node.style.get(enabled_key) is False:
        return 0.0
    return 1.0


def setStyle(node: DOMNode, style: Styles | None = None) -> None:
    node.style = dict(style or {})
    if not isinstance(node, DOMElement) or node.yogaNode is None:
        return

    yoga_node = node.yogaNode
    _apply_dimension(node, "width", node.style.get("width"))
    _apply_dimension(node, "height", node.style.get("height"))
    _apply_edge_values(node, "set_margin", "margin", node.style.get("margin"), node.style.get("marginX"), node.style.get("marginY"))
    _apply_edge_values(node, "set_padding", "padding", node.style.get("padding"), node.style.get("paddingX"), node.style.get("paddingY"))

    flex_direction = node.style.get("flexDirection")
    if flex_direction == "column":
        yoga_node.set_flex_direction(yoga.FLEX_DIRECTION_COLUMN)
    elif flex_direction == "column-reverse":
        yoga_node.set_flex_direction(yoga.FLEX_DIRECTION_COLUMN_REVERSE)
    elif flex_direction == "row-reverse":
        yoga_node.set_flex_direction(yoga.FLEX_DIRECTION_ROW_REVERSE)
    elif flex_direction == "row":
        yoga_node.set_flex_direction(yoga.FLEX_DIRECTION_ROW)

    if "flexGrow" in node.style:
        yoga_node.set_flex_grow(float(node.style["flexGrow"]))
    if "flexShrink" in node.style:
        yoga_node.set_flex_shrink(float(node.style["flexShrink"]))
    if "flexBasis" in node.style:
        basis = node.style["flexBasis"]
        if isinstance(basis, str) and basis.endswith("%"):
            yoga_node.set_flex_basis_percent(float(basis[:-1]))
        else:
            yoga_node.set_flex_basis(float(basis))

    flex_wrap = node.style.get("flexWrap")
    if flex_wrap == "wrap":
        yoga_node.set_flex_wrap(yoga.WRAP_WRAP)
    elif flex_wrap == "wrap-reverse":
        yoga_node.set_flex_wrap(yoga.WRAP_WRAP_REVERSE)
    elif flex_wrap == "nowrap":
        yoga_node.set_flex_wrap(yoga.WRAP_NO_WRAP)

    align_map = {
        "auto": yoga.ALIGN_AUTO,
        "flex-start": yoga.ALIGN_FLEX_START,
        "center": yoga.ALIGN_CENTER,
        "flex-end": yoga.ALIGN_FLEX_END,
        "stretch": yoga.ALIGN_STRETCH,
        "baseline": yoga.ALIGN_BASELINE,
        "space-between": yoga.ALIGN_SPACE_BETWEEN,
        "space-around": yoga.ALIGN_SPACE_AROUND,
        "space-evenly": yoga.ALIGN_SPACE_EVENLY,
    }
    justify_map = {
        "flex-start": yoga.JUSTIFY_FLEX_START,
        "center": yoga.JUSTIFY_CENTER,
        "flex-end": yoga.JUSTIFY_FLEX_END,
        "space-between": yoga.JUSTIFY_SPACE_BETWEEN,
        "space-around": yoga.JUSTIFY_SPACE_AROUND,
        "space-evenly": yoga.JUSTIFY_SPACE_EVENLY,
    }
    if node.style.get("alignItems") in align_map:
        yoga_node.set_align_items(align_map[node.style["alignItems"]])
    if node.style.get("alignSelf") in align_map:
        yoga_node.set_align_self(align_map[node.style["alignSelf"]])
    if node.style.get("alignContent") in align_map:
        yoga_node.set_align_content(align_map[node.style["alignContent"]])
    if node.style.get("justifyContent") in justify_map:
        yoga_node.set_justify_content(justify_map[node.style["justifyContent"]])

    if "columnGap" in node.style:
        yoga_node.set_gap(yoga.GUTTER_COLUMN, float(node.style["columnGap"]))
    if "rowGap" in node.style:
        yoga_node.set_gap(yoga.GUTTER_ROW, float(node.style["rowGap"]))
    if "gap" in node.style:
        yoga_node.set_gap(yoga.GUTTER_ALL, float(node.style["gap"]))

    position = node.style.get("position")
    if position == "absolute":
        yoga_node.set_position_type(yoga.POSITION_TYPE_ABSOLUTE)
    elif position == "static":
        yoga_node.set_position_type(yoga.POSITION_TYPE_STATIC)
    elif position == "relative":
        yoga_node.set_position_type(yoga.POSITION_TYPE_RELATIVE)

    for style_key, edge in (("left", yoga.EDGE_LEFT), ("right", yoga.EDGE_RIGHT), ("top", yoga.EDGE_TOP), ("bottom", yoga.EDGE_BOTTOM)):
        value = node.style.get(style_key)
        if value is None:
            continue
        if isinstance(value, str) and value.endswith("%"):
            yoga_node.set_position_percent(edge, float(value[:-1]))
        else:
            yoga_node.set_position(edge, float(value))

    if node.style.get("display") == "none":
        yoga_node.set_display(yoga.DISPLAY_NONE)
    else:
        yoga_node.set_display(yoga.DISPLAY_FLEX)

    for edge_key, edge, enabled_key in (
        ("borderLeft", yoga.EDGE_LEFT, "borderLeft"),
        ("borderRight", yoga.EDGE_RIGHT, "borderRight"),
        ("borderTop", yoga.EDGE_TOP, "borderTop"),
        ("borderBottom", yoga.EDGE_BOTTOM, "borderBottom"),
    ):
        yoga_node.set_border(edge, _resolve_border_width(node, edge_key, enabled_key))


def setTextNodeValue(node: TextNode, text: str) -> None:
    node.nodeValue = str(text)
    _mark_node_as_dirty(node)


def addLayoutListener(node: DOMElement, listener) -> None:
    node.internal_layoutListeners.add(listener)


def emitLayoutListeners(node: DOMElement) -> None:
    for listener in list(node.internal_layoutListeners):
        listener()


def squashTextNodes(node: DOMNode) -> str:
    if node.nodeName == "#text":
        return sanitizeAnsi(node.nodeValue)  # type: ignore[attr-defined]

    if not isinstance(node, DOMElement):
        return ""

    parts: list[str] = []
    for index, child in enumerate(node.childNodes):
        text = squashTextNodes(child)
        transform = getattr(child, "internal_transform", None)
        if callable(transform):
            text = transform(text, index)
        parts.append(text)
    return "".join(parts)


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
