"""
Reconciler for ink-python.

Manages the component tree and updates the DOM.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Union

from ink_python.component import VNode, create_vnode, is_component, render_component, Fragment
from ink_python.dom import (
    DOMElement,
    DOMNode,
    TextNode,
    append_child_node,
    create_node,
    create_text_node,
    insert_before_node,
    remove_child_node,
    set_attribute,
    set_style,
    set_text_node_value,
)
from ink_python.styles import Styles, apply_styles


class Reconciler:
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
        element: Union[VNode, str, None],
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

        # Clear existing children
        while dom_container.child_nodes:
            child = dom_container.child_nodes[0]
            remove_child_node(dom_container, child)
            if hasattr(child, "yoga_node") and child.yoga_node:
                child.yoga_node.free()

        # Render new tree
        if element is not None:
            self._reconcile_children(dom_container, [element])

        # Calculate layout
        if dom_container.yoga_node:
            self._calculate_layout(dom_container)

        # Trigger render callback
        if dom_container.on_render:
            dom_container.on_render()

        if callback:
            callback()

    def update_container_sync(
        self,
        element: Union[VNode, str, None],
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
        children: List[Union[VNode, str, None]],
    ) -> None:
        """
        Reconcile children into a parent node.

        Args:
            parent: The parent DOM element.
            children: List of child vnodes.
        """
        for child in children:
            if child is None:
                continue

            dom_node = self._create_dom_node(child, parent)
            if dom_node is not None:
                append_child_node(parent, dom_node)

    def _create_dom_node(
        self,
        vnode: Union[VNode, str],
        parent: DOMElement,
    ) -> Optional[DOMNode]:
        """
        Create a DOM node from a VNode.

        Args:
            vnode: The virtual node to materialize.
            parent: The parent DOM element.

        Returns:
            The created DOM node.
        """
        if isinstance(vnode, str):
            # Text content - should be inside Text component
            host_context = self._host_context_stack[-1]
            if not host_context.get("is_inside_text", False):
                raise ValueError(
                    f'Text string "{vnode[:20]}..." must be rendered inside <Text> component'
                )
            return create_text_node(vnode)

        node_type = vnode.type
        props = dict(vnode.props)
        children = list(vnode.children)

        # Handle function components
        if is_component(node_type):
            rendered = render_component(node_type, *children, **props)
            if rendered is None:
                return None
            if isinstance(rendered, str):
                host_context = self._host_context_stack[-1]
                if not host_context.get("is_inside_text", False):
                    raise ValueError(
                        f'Text string "{rendered[:20]}..." must be rendered inside <Text> component'
                    )
                return create_text_node(rendered)
            return self._create_dom_node(rendered, parent)

        # Handle Fragment
        if node_type is Fragment or node_type == "Fragment":
            # Fragments don't create their own node, just process children
            for child in children:
                dom_node = self._create_dom_node(child, parent)
                if dom_node is not None:
                    append_child_node(parent, dom_node)
            return None

        # Map component names to DOM element types
        element_name = self._get_element_name(node_type)
        if element_name is None:
            return None

        # Get host context
        host_context = self._host_context_stack[-1]
        is_inside_text = host_context.get("is_inside_text", False)

        # Validate Box inside Text
        if is_inside_text and element_name == "ink-box":
            raise ValueError("<Box> can't be nested inside <Text> component")

        # Determine actual element type
        actual_type = element_name
        if element_name == "ink-text" and is_inside_text:
            actual_type = "ink-virtual-text"

        # Create the DOM element
        dom_node = create_node(actual_type)

        # Update host context for children
        new_is_inside_text = actual_type in ("ink-text", "ink-virtual-text")
        new_host_context = {"is_inside_text": new_is_inside_text}

        # Apply props
        style = props.pop("style", {})
        if style:
            set_style(dom_node, style)
            if dom_node.yoga_node:
                apply_styles(dom_node.yoga_node, style)

        # Handle internal props
        if "internal_transform" in props:
            dom_node.internal_transform = props.pop("internal_transform")

        if "internal_static" in props:
            dom_node.internal_static = True
            self.root_node.is_static_dirty = True
            self.root_node.static_node = dom_node

        if "internal_accessibility" in props:
            dom_node.internal_accessibility = props.pop("internal_accessibility")

        # Set remaining attributes
        for key, value in props.items():
            if key != "children" and key != "ref":
                set_attribute(dom_node, key, value)

        # Push new host context and process children
        self._host_context_stack.append(new_host_context)
        try:
            for child in children:
                if child is None:
                    continue
                child_node = self._create_dom_node(child, dom_node)
                if child_node is not None:
                    append_child_node(dom_node, child_node)
        finally:
            self._host_context_stack.pop()

        return dom_node

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
        from ink_python import yoga_compat as yoga

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
_reconciler_instance: Optional[Reconciler] = None


def get_reconciler(root_node: Optional[DOMElement] = None) -> Reconciler:
    """
    Get or create the reconciler instance.

    Args:
        root_node: Optional root node for a new reconciler.

    Returns:
        The Reconciler instance.
    """
    global _reconciler_instance
    if _reconciler_instance is None and root_node is not None:
        _reconciler_instance = Reconciler(root_node)
    return _reconciler_instance


def create_reconciler(root_node: DOMElement) -> Reconciler:
    """
    Create a new reconciler instance.

    Args:
        root_node: The root DOM element.

    Returns:
        A new Reconciler instance.
    """
    return Reconciler(root_node)
