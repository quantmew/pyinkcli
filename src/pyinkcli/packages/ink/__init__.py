"""Ink host renderer internals grouped under a package-style namespace."""

from pyinkcli.packages.ink.dom import (
    DOMElement,
    DOMNode,
    DOMNodeAttribute,
    ElementNames,
    NodeNames,
    TextNode,
    addLayoutListener,
    appendChildNode,
    createNode,
    createTextNode,
    emitLayoutListeners,
    insertBeforeNode,
    removeChildNode,
    setAttribute,
    setStyle,
    setTextNodeValue,
    squashTextNodes,
)
from pyinkcli.packages.ink.output import Output
from pyinkcli.packages.ink.styles import Styles, TextWrap, apply_styles
from pyinkcli.packages.ink.host_config import ReconcilerHostConfig
from pyinkcli.packages.ink.render_background import renderBackground
from pyinkcli.packages.ink.render_border import renderBorder
from pyinkcli.packages.ink.render_node_to_output import (
    OutputTransformer,
    applyPaddingToText,
    indentString,
    renderNodeToOutput,
    renderNodeToScreenReaderOutput,
)
from pyinkcli.packages.ink.renderer import RenderResult, render

__all__ = [
    "DOMElement",
    "DOMNode",
    "DOMNodeAttribute",
    "ElementNames",
    "NodeNames",
    "TextNode",
    "addLayoutListener",
    "appendChildNode",
    "applyPaddingToText",
    "createNode",
    "createTextNode",
    "emitLayoutListeners",
    "indentString",
    "insertBeforeNode",
    "Output",
    "OutputTransformer",
    "ReconcilerHostConfig",
    "removeChildNode",
    "render",
    "renderBackground",
    "renderBorder",
    "RenderResult",
    "renderNodeToOutput",
    "renderNodeToScreenReaderOutput",
    "setAttribute",
    "setStyle",
    "setTextNodeValue",
    "squashTextNodes",
    "Styles",
    "TextWrap",
    "apply_styles",
]
