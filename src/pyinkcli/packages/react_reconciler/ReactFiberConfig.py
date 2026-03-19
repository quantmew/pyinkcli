"""Host config surface aligned with ReactFiberConfig responsibilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from pyinkcli.packages.ink.dom import (
    AccessibilityInfo,
    DOMElement,
    DOMNode,
    TextNode,
    appendChildNode,
    createNode,
    createTextNode,
    insertBeforeNode,
    removeChildNode,
    setAttribute,
    setStyle,
    setTextNodeValue,
)
from pyinkcli.packages.ink.host_config import ReconcilerHostConfig
from pyinkcli.packages.ink.styles import apply_styles
from pyinkcli.packages.react_reconciler.ReactFiberReconciler import cleanupYogaNode

if TYPE_CHECKING:
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler


def getExistingChild(
    _reconciler: "_Reconciler",
    parent: DOMElement,
    dom_index: int,
) -> Optional[DOMNode]:
    if 0 <= dom_index < len(parent.childNodes):
        return parent.childNodes[dom_index]
    return None


def findMatchingChild(
    reconciler: "_Reconciler",
    parent: DOMElement,
    dom_index: int,
    actual_type: str,
    vnode_key: Optional[str],
) -> Optional[DOMNode]:
    existing = getExistingChild(reconciler, parent, dom_index)
    if (
        isinstance(existing, DOMElement)
        and existing.nodeName == actual_type
        and existing.key == vnode_key
    ):
        return existing

    if vnode_key is None:
        return existing

    for child in parent.childNodes[dom_index + 1:]:
        if (
            isinstance(child, DOMElement)
            and child.nodeName == actual_type
            and child.key == vnode_key
        ):
            return child

    return existing


def disposeNode(reconciler: "_Reconciler", node: DOMNode) -> None:
    if isinstance(node, DOMElement):
        while node.childNodes:
            child = node.childNodes[0]
            removeChildNode(node, child)
            disposeNode(reconciler, child)

        if reconciler.root_node.staticNode is node:
            reconciler.root_node.staticNode = None

        cleanupYogaNode(node.yogaNode)


def insertOrReplaceChild(
    reconciler: "_Reconciler",
    parent: DOMElement,
    child: DOMNode,
    dom_index: int,
) -> None:
    existing = getExistingChild(reconciler, parent, dom_index)
    if existing is child:
        return

    if existing is None:
        appendChildNode(parent, child)
        return

    if child.parentNode is parent:
        insertBeforeNode(parent, child, existing)
        return

    insertBeforeNode(parent, child, existing)
    removeChildNode(parent, existing)
    disposeNode(reconciler, existing)


def applyProps(
    reconciler: "_Reconciler",
    dom_node: DOMElement,
    props: dict[str, Any],
    vnode_key: Optional[str],
) -> None:
    style = props.pop("style", {})
    setStyle(dom_node, style)
    if dom_node.yogaNode:
        apply_styles(dom_node.yogaNode, style)

    dom_node.key = vnode_key
    dom_node.internal_transform = props.pop("internal_transform", None)

    internal_static = bool(props.pop("internal_static", False))
    dom_node.internal_static = internal_static
    if internal_static:
        reconciler.root_node.isStaticDirty = True
        reconciler.root_node.staticNode = dom_node
    elif reconciler.root_node.staticNode is dom_node:
        reconciler.root_node.staticNode = None

    internal_accessibility = props.pop("internal_accessibility", None)
    if internal_accessibility is None:
        dom_node.internal_accessibility = {}
    else:
        dom_node.internal_accessibility = {
            key: value
            for key, value in {
                "role": internal_accessibility.get("role"),
                "state": internal_accessibility.get("state"),
            }.items()
            if value is not None
        }

    new_attributes = {
        key: value
        for key, value in props.items()
        if key not in ("children", "ref")
    }

    for key in list(dom_node.attributes.keys()):
        if key not in new_attributes:
            del dom_node.attributes[key]

    for key, value in new_attributes.items():
        setAttribute(dom_node, key, value)


def reconcileTextNode(
    reconciler: "_Reconciler",
    parent: DOMElement,
    text: str,
    dom_index: int,
) -> None:
    existing = getExistingChild(reconciler, parent, dom_index)

    if isinstance(existing, TextNode):
        setTextNodeValue(existing, text)
        return

    new_node = createTextNode(text)
    insertOrReplaceChild(reconciler, parent, new_node, dom_index)


def reconcileElementNode(
    reconciler: "_Reconciler",
    parent: DOMElement,
    actual_type: str,
    props: dict[str, Any],
    dom_index: int,
    vnode_key: Optional[str],
) -> DOMElement:
    current_existing = getExistingChild(reconciler, parent, dom_index)
    existing = findMatchingChild(reconciler, parent, dom_index, actual_type, vnode_key)

    if isinstance(existing, DOMElement) and existing.nodeName == actual_type:
        dom_node = existing
        if current_existing is not None and current_existing is not dom_node:
            insertBeforeNode(parent, dom_node, current_existing)
    else:
        dom_node = createNode(actual_type)
        insertOrReplaceChild(reconciler, parent, dom_node, dom_index)

    applyProps(reconciler, dom_node, props, vnode_key)
    return dom_node


def removeExtraChildren(
    reconciler: "_Reconciler",
    parent: DOMElement,
    start_index: int,
) -> None:
    while len(parent.childNodes) > start_index:
        child = parent.childNodes[start_index]
        removeChildNode(parent, child)
        disposeNode(reconciler, child)


__all__ = [
    "ReconcilerHostConfig",
    "applyProps",
    "disposeNode",
    "findMatchingChild",
    "getExistingChild",
    "insertOrReplaceChild",
    "reconcileElementNode",
    "reconcileTextNode",
    "removeExtraChildren",
]
