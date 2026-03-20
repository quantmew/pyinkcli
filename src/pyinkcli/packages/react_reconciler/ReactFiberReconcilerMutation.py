"""Mutation and child reconciliation composition methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyinkcli.packages.ink.dom import DOMElement, DOMNode
from pyinkcli.packages.react_reconciler.ReactChildFiber import (
    getChildPathToken as _get_child_path_token_impl,
)
from pyinkcli.packages.react_reconciler.ReactChildFiber import (
    getElementName as _get_element_name_impl,
)
from pyinkcli.packages.react_reconciler.ReactChildFiber import (
    reconcileChild as _reconcile_child_impl,
)
from pyinkcli.packages.react_reconciler.ReactChildFiber import (
    reconcileChildren as _reconcile_children_impl,
)
from pyinkcli.packages.react_reconciler.ReactFiberConfig import (
    disposeNode as _dispose_node_impl,
)
from pyinkcli.packages.react_reconciler.ReactFiberConfig import (
    getExistingChild as _get_existing_child_impl,
)
from pyinkcli.packages.react_reconciler.ReactFiberConfig import (
    reconcileElementNode as _reconcile_element_node_impl,
)
from pyinkcli.packages.react_reconciler.ReactFiberConfig import (
    reconcileTextNode as _reconcile_text_node_impl,
)
from pyinkcli.packages.react_reconciler.ReactFiberConfig import (
    removeExtraChildren as _remove_extra_children_impl,
)
from pyinkcli.packages.react_reconciler.ReactFiberContainerUpdate import (
    calculateLayout as _calculate_layout_impl,
)

if TYPE_CHECKING:
    from pyinkcli.component import RenderableNode


class ReactFiberReconcilerMutation:
    def _reconcile_children(
        self,
        parent: DOMElement,
        children: list[RenderableNode],
        path: tuple[Any, ...],
        dom_index: int,
        devtools_parent_id: str,
    ) -> int:
        return _reconcile_children_impl(
            self,
            parent,
            children,
            path,
            dom_index,
            devtools_parent_id,
        )

    def _reconcile_child(
        self,
        vnode: RenderableNode,
        parent: DOMElement,
        path: tuple[Any, ...],
        dom_index: int,
        devtools_parent_id: str,
    ) -> int:
        return _reconcile_child_impl(
            self,
            vnode,
            parent,
            path,
            dom_index,
            devtools_parent_id,
        )

    def _reconcile_text_node(
        self,
        parent: DOMElement,
        text: str,
        dom_index: int,
    ) -> None:
        _reconcile_text_node_impl(self, parent, text, dom_index)

    def _reconcile_element_node(
        self,
        parent: DOMElement,
        actual_type: str,
        props: dict[str, Any],
        children: list[RenderableNode],
        path: tuple[Any, ...],
        dom_index: int,
        vnode_key: str | None,
    ) -> DOMElement:
        del children, path
        return _reconcile_element_node_impl(
            self,
            parent,
            actual_type,
            props,
            dom_index,
            vnode_key,
        )

    def _apply_props(
        self,
        dom_node: DOMElement,
        props: dict[str, Any],
        vnode_key: str | None,
    ) -> None:
        from pyinkcli.packages.react_reconciler.ReactFiberConfig import applyProps

        applyProps(self, dom_node, props, vnode_key)

    def _get_existing_child(
        self,
        parent: DOMElement,
        dom_index: int,
    ) -> DOMNode | None:
        return _get_existing_child_impl(self, parent, dom_index)

    def _find_matching_child(
        self,
        parent: DOMElement,
        dom_index: int,
        actual_type: str,
        vnode_key: str | None,
    ) -> DOMNode | None:
        from pyinkcli.packages.react_reconciler.ReactFiberConfig import findMatchingChild

        return findMatchingChild(self, parent, dom_index, actual_type, vnode_key)

    def _insert_or_replace_child(
        self,
        parent: DOMElement,
        child: DOMNode,
        dom_index: int,
    ) -> None:
        from pyinkcli.packages.react_reconciler.ReactFiberConfig import insertOrReplaceChild

        insertOrReplaceChild(self, parent, child, dom_index)

    def _remove_extra_children(self, parent: DOMElement, start_index: int) -> None:
        _remove_extra_children_impl(self, parent, start_index)

    def _dispose_node(self, node: DOMNode) -> None:
        _dispose_node_impl(self, node)

    def _get_child_path_token(
        self,
        child: RenderableNode,
        index: int,
    ) -> Any:
        return _get_child_path_token_impl(self, child, index)

    def _get_element_name(self, node_type: Any) -> str | None:
        return _get_element_name_impl(self, node_type)

    def _calculate_layout(self, root: DOMElement) -> None:
        _calculate_layout_impl(self, root)


__all__ = ["ReactFiberReconcilerMutation"]
