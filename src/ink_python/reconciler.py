"""Reconciler for ink-python."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

from ink_python._component_runtime import (
    _Fragment,
    createElement,
    isElement,
    is_component,
    renderComponent,
)
from ink_python._suspense_runtime import SuspendSignal
from ink_python.dom import (
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
from ink_python.styles import Styles, apply_styles
from ink_python.hooks._runtime import (
    _begin_component_render,
    _end_component_render,
    _finish_hook_state,
)

if TYPE_CHECKING:
    from ink_python.component import RenderableNode


class _Reconciler:
    """
    Custom reconciler for rendering components to the terminal DOM.

    Similar to React's reconciler but adapted for terminal output.
    """

    def __init__(self, root_node: DOMElement):
        self.root_node = root_node
        self._current_fiber: Optional[Any] = None
        self._host_context_stack: List[Dict[str, Any]] = [{"is_inside_text": False}]

    def create_container(
        self,
        container: DOMElement,
        tag: int = 0,
        hydrate: bool = False,
    ) -> Any:
        """
        Create a container for rendering.

        Args:
            container: The root DOM element.
            tag: Legacy (0) or Concurrent (1) mode.
            hydrate: Whether to hydrate existing content.

        Returns:
            The container (fiber root).
        """
        return {"container": container, "tag": tag}

    def update_container(
        self,
        element: "RenderableNode",
        container: Dict[str, Any],
        parent_component: Optional[Any] = None,
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Update the container with a new element tree.

        Args:
            element: The new element to render.
            container: The container info.
            parent_component: Parent component reference.
            callback: Optional callback after update.
        """
        dom_container = container.get("container", self.root_node)

        try:
            next_index = 0
            if element is not None:
                next_index = self._reconcile_children(dom_container, [element], (), 0)

            self._remove_extra_children(dom_container, next_index)

            if dom_container.yoga_node:
                self._calculate_layout(dom_container)
        finally:
            _finish_hook_state()

        # Trigger render callback
        if dom_container.on_render:
            dom_container.on_render()

        if callback:
            callback()

    def update_container_sync(
        self,
        element: "RenderableNode",
        container: Dict[str, Any],
        parent_component: Optional[Any] = None,
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """Synchronous container update."""
        self.update_container(element, container, parent_component, callback)

    def flush_sync_work(self) -> None:
        """Flush any pending synchronous work."""
        pass

    def _reconcile_children(
        self,
        parent: DOMElement,
        children: List["RenderableNode"],
        path: tuple[Any, ...],
        dom_index: int,
    ) -> int:
        """
        Reconcile children into a parent node.

        Args:
            parent: The parent DOM element.
            children: List of child vnodes.
        """
        for index, child in enumerate(children):
            child_path = path + (self._get_child_path_token(child, index),)
            dom_index = self._reconcile_child(child, parent, child_path, dom_index)

        return dom_index

    def _reconcile_child(
        self,
        vnode: "RenderableNode",
        parent: DOMElement,
        path: tuple[Any, ...],
        dom_index: int,
    ) -> int:
        if vnode is None:
            return dom_index

        if isinstance(vnode, str):
            host_context = self._host_context_stack[-1]
            if not host_context.get("is_inside_text", False):
                raise ValueError(
                    f'Text string "{vnode[:20]}..." must be rendered inside <Text> component'
                )

            self._reconcile_text_node(parent, vnode, dom_index)
            return dom_index + 1

        node_type = vnode.type
        props = dict(vnode.props)
        children = list(vnode.children)

        if node_type == "__ink-suspense__":
            fallback = props.get("fallback")
            try:
                return self._reconcile_children(parent, children, path, dom_index)
            except SuspendSignal:
                if fallback is None:
                    return dom_index
                return self._reconcile_child(
                    fallback,
                    parent,
                    path + ("fallback",),
                    dom_index,
                )

        if is_component(node_type):
            component_id = self._get_component_instance_id(node_type, vnode, path)
            _begin_component_render(component_id)
            try:
                rendered = renderComponent(node_type, *children, **props)
            finally:
                _end_component_render()

            return self._reconcile_child(rendered, parent, path, dom_index)

        if node_type is _Fragment or node_type == "Fragment":
            return self._reconcile_children(parent, children, path, dom_index)

        element_name = self._get_element_name(node_type)
        if element_name is None:
            return dom_index

        host_context = self._host_context_stack[-1]
        is_inside_text = host_context.get("is_inside_text", False)

        if is_inside_text and element_name == "ink-box":
            raise ValueError("<Box> can't be nested inside <Text> component")

        actual_type = element_name
        if element_name == "ink-text" and is_inside_text:
            actual_type = "ink-virtual-text"

        dom_node = self._reconcile_element_node(
            parent,
            actual_type,
            props,
            children,
            path,
            dom_index,
            vnode.key,
        )

        new_host_context = {
            "is_inside_text": actual_type in ("ink-text", "ink-virtual-text")
        }
        self._host_context_stack.append(new_host_context)
        try:
            next_child_index = self._reconcile_children(dom_node, children, path, 0)
            self._remove_extra_children(dom_node, next_child_index)
        finally:
            self._host_context_stack.pop()

        return dom_index + 1

    def _reconcile_text_node(
        self,
        parent: DOMElement,
        text: str,
        dom_index: int,
    ) -> None:
        existing = self._get_existing_child(parent, dom_index)

        if isinstance(existing, TextNode):
            setTextNodeValue(existing, text)
            return

        new_node = createTextNode(text)
        self._insert_or_replace_child(parent, new_node, dom_index)

    def _reconcile_element_node(
        self,
        parent: DOMElement,
        actual_type: str,
        props: dict[str, Any],
        children: list["RenderableNode"],
        path: tuple[Any, ...],
        dom_index: int,
        vnode_key: Optional[str],
    ) -> DOMElement:
        current_existing = self._get_existing_child(parent, dom_index)
        existing = self._find_matching_child(parent, dom_index, actual_type, vnode_key)

        if isinstance(existing, DOMElement) and existing.node_name == actual_type:
            dom_node = existing
            if current_existing is not None and current_existing is not dom_node:
                insertBeforeNode(parent, dom_node, current_existing)
        else:
            dom_node = createNode(actual_type)
            self._insert_or_replace_child(parent, dom_node, dom_index)

        self._apply_props(dom_node, props, vnode_key)
        return dom_node

    def _apply_props(
        self,
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
            self.root_node.is_static_dirty = True
            self.root_node.static_node = dom_node
        elif self.root_node.static_node is dom_node:
            self.root_node.static_node = None

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

    def _get_existing_child(
        self,
        parent: DOMElement,
        dom_index: int,
    ) -> Optional[DOMNode]:
        if 0 <= dom_index < len(parent.child_nodes):
            return parent.child_nodes[dom_index]

        return None

    def _find_matching_child(
        self,
        parent: DOMElement,
        dom_index: int,
        actual_type: str,
        vnode_key: Optional[str],
    ) -> Optional[DOMNode]:
        existing = self._get_existing_child(parent, dom_index)
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

    def _insert_or_replace_child(
        self,
        parent: DOMElement,
        child: DOMNode,
        dom_index: int,
    ) -> None:
        existing = self._get_existing_child(parent, dom_index)
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
        self._dispose_node(existing)

    def _remove_extra_children(self, parent: DOMElement, start_index: int) -> None:
        while len(parent.child_nodes) > start_index:
            child = parent.child_nodes[start_index]
            removeChildNode(parent, child)
            self._dispose_node(child)

    def _dispose_node(self, node: DOMNode) -> None:
        if isinstance(node, DOMElement):
            while node.child_nodes:
                child = node.child_nodes[0]
                removeChildNode(node, child)
                self._dispose_node(child)

            if self.root_node.static_node is node:
                self.root_node.static_node = None

            if node.yoga_node is not None and hasattr(node.yoga_node, "free"):
                node.yoga_node.free()

    def _get_component_instance_id(
        self,
        component_type: Any,
        vnode: "RenderableNode",
        path: tuple[Any, ...],
    ) -> str:
        assert isElement(vnode)
        component_name = getattr(component_type, "_component_name", None)
        if component_name is None:
            component_name = getattr(component_type, "__name__", repr(component_type))

        key = vnode.key if vnode.key is not None else ""
        return f"{component_name}:{'.'.join(str(part) for part in path)}:{key}"

    def _get_child_path_token(
        self,
        child: "RenderableNode",
        index: int,
    ) -> Any:
        if isElement(child) and child.key is not None:
            return f"key:{child.key}"

        return index

    def _get_element_name(self, node_type: Any) -> Optional[str]:
        """
        Get the DOM element name for a component type.

        Args:
            node_type: The component type.

        Returns:
            The element name or None.
        """
        if isinstance(node_type, str):
            # Map common names
            type_map = {
                "Box": "ink-box",
                "Text": "ink-text",
                "ink-box": "ink-box",
                "ink-text": "ink-text",
            }
            return type_map.get(node_type, node_type)

        return None

    def _calculate_layout(self, root: DOMElement) -> None:
        """
        Calculate the Yoga layout for the tree.

        Args:
            root: The root element.
        """
        from ink_python import _yoga as yoga

        if root.yoga_node:
            root.yoga_node.calculate_layout(
                yoga.UNDEFINED,
                yoga.UNDEFINED,
                yoga.DIRECTION_LTR,
            )

        # Emit layout listeners
        if root.node_name == "ink-root" and root.internal_layout_listeners:
            for listener in root.internal_layout_listeners:
                listener()


# Singleton reconciler instance
_reconciler_instance: Optional[_Reconciler] = None
currentUpdatePriority = 0


def diff(before: Dict[str, Any], after: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if before == after:
        return None
    if not before:
        return after
    changed: Dict[str, Any] = {}
    changed_any = False
    for key in before:
        if key not in after:
            changed[key] = None
            changed_any = True
    for key, value in after.items():
        if before.get(key) != value:
            changed[key] = value
            changed_any = True
    return changed if changed_any else None


def cleanupYogaNode(node: Optional[Any]) -> None:
    if node is None:
        return
    unset = getattr(node, "unset_measure_func", None) or getattr(node, "unsetMeasureFunc", None)
    if callable(unset):
        unset()
    free_recursive = getattr(node, "free_recursive", None) or getattr(node, "freeRecursive", None)
    if callable(free_recursive):
        free_recursive()
        return
    free = getattr(node, "free", None)
    if callable(free):
        free()


def loadPackageJson() -> dict[str, str]:
    package_json = Path(__file__).resolve().parents[2] / "package.json"
    if package_json.exists():
        parsed = json.loads(package_json.read_text())
        return {
            "name": parsed.get("name", "ink-python"),
            "version": parsed.get("version", "0.1.0"),
        }
    return {"name": "ink-python", "version": "0.1.0"}


packageInfo = loadPackageJson()


def getReconciler(root_node: Optional[DOMElement] = None) -> _Reconciler:
    """
    Get or create the reconciler instance.

    Args:
        root_node: Optional root node for a new reconciler.

    Returns:
        The Reconciler instance.
    """
    global _reconciler_instance
    if _reconciler_instance is None and root_node is not None:
        _reconciler_instance = _Reconciler(root_node)
    return _reconciler_instance


def createReconciler(root_node: DOMElement) -> _Reconciler:
    """
    Create a new reconciler instance.

    Args:
        root_node: The root DOM element.

    Returns:
        A new Reconciler instance.
    """
    return _Reconciler(root_node)
