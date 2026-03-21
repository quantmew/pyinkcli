"""Host config surface aligned with ReactFiberConfig responsibilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyinkcli.packages.ink.dom import (
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
from pyinkcli.packages.react_reconciler.ReactFiberFlags import Deletion, Placement, Ref, Update
from pyinkcli.packages.react_reconciler.ReactFiberReconciler import cleanupYogaNode

if TYPE_CHECKING:
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler


def _mark_fiber_flag(reconciler: _Reconciler, flag: int) -> None:
    fiber = getattr(reconciler, "_current_fiber", None)
    if fiber is not None:
        fiber.flags |= flag


def _record_prepared_effect(
    reconciler: _Reconciler,
    tag: str,
    *,
    phase: str = "mutation",
    node_type: str | None = None,
    **payload: Any,
) -> None:
    del reconciler, tag, phase, node_type, payload


def getExistingChild(
    _reconciler: _Reconciler,
    parent: DOMElement,
    dom_index: int,
) -> DOMNode | None:
    if 0 <= dom_index < len(parent.childNodes):
        return parent.childNodes[dom_index]
    return None


def findMatchingChild(
    reconciler: _Reconciler,
    parent: DOMElement,
    dom_index: int,
    actual_type: str,
    vnode_key: str | None,
) -> DOMNode | None:
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


def disposeNode(reconciler: _Reconciler, node: DOMNode) -> None:
    if isinstance(node, DOMElement):
        while node.childNodes:
            child = node.childNodes[0]
            removeChildNode(node, child)
            disposeNode(reconciler, child)

        if reconciler.root_node.staticNode is node:
            reconciler.root_node.staticNode = None

        cleanupYogaNode(node.yogaNode)


def insertOrReplaceChild(
    reconciler: _Reconciler,
    parent: DOMElement,
    child: DOMNode,
    dom_index: int,
) -> None:
    existing = getExistingChild(reconciler, parent, dom_index)
    if existing is child:
        return

    if existing is None:
        appendChildNode(parent, child)
        _mark_fiber_flag(reconciler, Placement)
        _record_prepared_effect(
            reconciler,
            "append_child",
            phase="mutation",
            node_type=parent.nodeName,
            parent=parent.nodeName,
        )
        return

    if child.parentNode is parent:
        insertBeforeNode(parent, child, existing)
        _mark_fiber_flag(reconciler, Placement)
        _record_prepared_effect(
            reconciler,
            "move_child",
            phase="mutation",
            node_type=parent.nodeName,
            parent=parent.nodeName,
        )
        return

    insertBeforeNode(parent, child, existing)
    removeChildNode(parent, existing)
    disposeNode(reconciler, existing)
    _mark_fiber_flag(reconciler, Placement | Deletion)
    _record_prepared_effect(
        reconciler,
        "replace_child",
        phase="mutation",
        node_type=parent.nodeName,
        parent=parent.nodeName,
    )


def applyProps(
    reconciler: _Reconciler,
    dom_node: DOMElement,
    props: dict[str, Any],
    vnode_key: str | None,
) -> None:
    previous_ref = getattr(dom_node, "internal_ref", None)
    ref = props.pop("ref", None)
    style = props.pop("style", {})
    setStyle(dom_node, style)
    if dom_node.yogaNode:
        apply_styles(dom_node.yogaNode, style)

    dom_node.key = vnode_key
    dom_node.internal_ref = ref
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
        if key != "children"
    }

    for key in list(dom_node.attributes.keys()):
        if key not in new_attributes:
            del dom_node.attributes[key]

    for key, value in new_attributes.items():
        setAttribute(dom_node, key, value)
    _mark_fiber_flag(reconciler, Update)
    current_fiber = getattr(reconciler, "_current_fiber", None)
    if previous_ref is not None and previous_ref is not ref and current_fiber is not None:
        current_fiber.ref_detachments.append(previous_ref)
        _mark_fiber_flag(reconciler, Ref)
    if ref is not None:
        _mark_fiber_flag(reconciler, Ref)
    _record_prepared_effect(
        reconciler,
        "apply_props",
        phase="mutation",
        node_type=dom_node.nodeName,
    )


def reconcileTextNode(
    reconciler: _Reconciler,
    parent: DOMElement,
    text: str,
    dom_index: int,
) -> TextNode:
    existing = getExistingChild(reconciler, parent, dom_index)

    if isinstance(existing, TextNode):
        setTextNodeValue(existing, text)
        _mark_fiber_flag(reconciler, Update)
        _record_prepared_effect(
            reconciler,
            "update_text",
            phase="mutation",
            node_type="#text",
        )
        return existing

    new_node = createTextNode(text)
    insertOrReplaceChild(reconciler, parent, new_node, dom_index)
    return new_node


def reconcileElementNode(
    reconciler: _Reconciler,
    parent: DOMElement,
    actual_type: str,
    props: dict[str, Any],
    dom_index: int,
    vnode_key: str | None,
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
    reconciler: _Reconciler,
    parent: DOMElement,
    start_index: int,
) -> None:
    while len(parent.childNodes) > start_index:
        child = parent.childNodes[start_index]
        current_fiber = getattr(reconciler, "_current_fiber", None)
        if current_fiber is not None:
            current_fiber.deletions.append(child)  # type: ignore[arg-type]
        removeChildNode(parent, child)
        disposeNode(reconciler, child)
        _mark_fiber_flag(reconciler, Deletion)


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
