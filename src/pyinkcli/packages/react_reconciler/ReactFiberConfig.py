"""Host config surface aligned with ReactFiberConfig responsibilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from pyinkcli.packages.react_dom.host import (
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
    apply_styles,
)
from pyinkcli.packages.react_dom.host_config import ReconcilerHostConfig

if TYPE_CHECKING:
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler


def getExistingChild(
    _reconciler: "_Reconciler",
    parent: DOMElement,
    dom_index: int,
) -> Optional[DOMNode]:
    if 0 <= dom_index < len(parent.child_nodes):
        return parent.child_nodes[dom_index]
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
        and existing.node_name == actual_type
        and existing.internal_key == vnode_key
    ):
        return existing

    if vnode_key is None:
        return existing

    for child in parent.child_nodes[dom_index + 1:]:
        if (
            isinstance(child, DOMElement)
            and child.node_name == actual_type
            and child.internal_key == vnode_key
        ):
            return child

    return existing


def disposeNode(reconciler: "_Reconciler", node: DOMNode) -> None:
    if isinstance(node, DOMElement):
        while node.child_nodes:
            child = node.child_nodes[0]
            removeChildNode(node, child)
            disposeNode(reconciler, child)

        if reconciler.root_node.static_node is node:
            reconciler.root_node.static_node = None

        if node.yoga_node is not None and hasattr(node.yoga_node, "free"):
            node.yoga_node.free()


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

    if child.parent_node is parent:
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
    if dom_node.yoga_node:
        apply_styles(dom_node.yoga_node, style)

    dom_node.internal_key = vnode_key
    dom_node.internal_transform = props.pop("internal_transform", None)

    internal_static = bool(props.pop("internal_static", False))
    dom_node.internal_static = internal_static
    if internal_static:
        reconciler.root_node.is_static_dirty = True
        reconciler.root_node.static_node = dom_node
    elif reconciler.root_node.static_node is dom_node:
        reconciler.root_node.static_node = None

    internal_accessibility = props.pop("internal_accessibility", None)
    if internal_accessibility is None:
        dom_node.internal_accessibility = AccessibilityInfo()
    elif isinstance(internal_accessibility, AccessibilityInfo):
        dom_node.internal_accessibility = internal_accessibility
    else:
        dom_node.internal_accessibility = AccessibilityInfo(
            role=internal_accessibility.get("role"),
            state=internal_accessibility.get("state"),
        )

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

    if isinstance(existing, DOMElement) and existing.node_name == actual_type:
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
    while len(parent.child_nodes) > start_index:
        child = parent.child_nodes[start_index]
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
