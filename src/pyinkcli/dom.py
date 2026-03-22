from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DOMNodeAttribute:
    name: str
    value: Any


@dataclass
class DOMNode:
    nodeName: str
    childNodes: list["DOMNode"] = field(default_factory=list)
    parentNode: "DOMNode | None" = None
    attributes: dict[str, Any] = field(default_factory=dict)
    style: dict[str, Any] = field(default_factory=dict)
    internal_layoutListeners: list[Any] = field(default_factory=list)
    onComputeLayout: Any = None
    onRender: Any = None
    onImmediateRender: Any = None


@dataclass
class DOMElement(DOMNode):
    pass


@dataclass
class TextNode(DOMNode):
    nodeValue: str = ""


ElementNames = str
NodeNames = str


def createNode(node_name: str) -> DOMElement:
    return DOMElement(nodeName=node_name)


def appendChildNode(parent: DOMNode, child: DOMNode) -> None:
    child.parentNode = parent
    parent.childNodes.append(child)


def insertBeforeNode(parent: DOMNode, child: DOMNode, before: DOMNode) -> None:
    child.parentNode = parent
    index = parent.childNodes.index(before)
    parent.childNodes.insert(index, child)


def removeChildNode(parent: DOMNode, child: DOMNode) -> None:
    parent.childNodes.remove(child)
    child.parentNode = None


def setAttribute(node: DOMNode, name: str, value: Any) -> None:
    node.attributes[name] = value
    setattr(node, name, value)


def setStyle(node: DOMNode, style: dict[str, Any]) -> None:
    node.style.update(style)


def createTextNode(value: str) -> TextNode:
    return TextNode(nodeName="#text", nodeValue=value)


def setTextNodeValue(node: TextNode, value: str) -> None:
    node.nodeValue = value


def addLayoutListener(node: DOMNode, listener) -> None:
    node.internal_layoutListeners.append(listener)


def emitLayoutListeners(node: DOMNode) -> None:
    for listener in list(node.internal_layoutListeners):
        listener()


from .squash_text_nodes import squashTextNodes  # noqa: E402

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

