"""
Component base classes for ink-python.

Provides the foundation for creating React-like components in Python.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Union,
)


@dataclass
class VNode:
    """
    Virtual DOM node representation.

    Similar to React's virtual DOM nodes.
    """

    type: Union[str, Callable, type]
    props: Dict[str, Any] = field(default_factory=dict)
    children: List[Union[VNode, str, None]] = field(default_factory=list)
    key: Optional[str] = None

    def __hash__(self) -> int:
        return id(self)


def create_vnode(
    type: Union[str, Callable, type],
    *children: Union[VNode, str, None],
    key: Optional[str] = None,
    **props: Any,
) -> VNode:
    """
    Create a virtual DOM node.

    Args:
        type: The component type (string for built-in, callable for function component).
        *children: Child nodes.
        key: Optional key for reconciliation.
        **props: Component properties.

    Returns:
        A new VNode instance.
    """
    processed_children: List[Union[VNode, str, None]] = []
    for child in children:
        if child is None:
            continue
        if isinstance(child, (VNode, str)):
            processed_children.append(child)
        elif isinstance(child, (list, tuple)):
            for subchild in child:
                if subchild is None:
                    continue
                processed_children.append(subchild)
        else:
            processed_children.append(str(child))

    return VNode(
        type=type,
        props=props,
        children=processed_children,
        key=key,
    )


class Component:
    """
    Base class for class-based components.

    For most use cases, prefer functional components using @component decorator.
    """

    def __init__(self, **props: Any):
        self.props = props
        self.state: Dict[str, Any] = {}
        self._state_version = 0

    def render(self) -> Union[VNode, str, None]:
        """Render the component. Override in subclasses."""
        return None

    def set_state(self, **kwargs: Any) -> None:
        """Update component state."""
        self.state.update(kwargs)
        self._state_version += 1


def component(
    func: Optional[Callable] = None, *, name: Optional[str] = None
) -> Callable:
    """
    Decorator to create a functional component.

    Args:
        func: The component function.
        name: Optional component name.

    Returns:
        A component function.
    """

    def wrapper(fn: Callable) -> Callable:
        fn._is_component = True
        fn._component_name = name or fn.__name__
        return fn

    if func is not None:
        return wrapper(func)
    return wrapper


def is_component(obj: Any) -> bool:
    """Check if an object is a component."""
    return callable(obj) and getattr(obj, "_is_component", False)


def render_component(
    component: Union[Callable, Component, VNode, str, None],
    *children: Union[VNode, str, None],
    **props: Any,
) -> Union[VNode, str, None]:
    """
    Render a component to a VNode.

    Args:
        component: The component to render.
        *children: Child nodes to pass to the component.
        **props: Additional props to pass.

    Returns:
        The rendered VNode or string.
    """
    if component is None:
        return None

    if isinstance(component, str):
        return component

    if isinstance(component, VNode):
        return component

    if isinstance(component, Component):
        return component.render()

    if callable(component):
        result = component(*children, **props)
        if isinstance(result, (VNode, str)):
            return result
        if result is None:
            return None
        return str(result)

    return str(component)


# JSX-like syntax helpers
def h(
    type: Union[str, Callable, type],
    *children: Union[VNode, str, None],
    key: Optional[str] = None,
    **props: Any,
) -> VNode:
    """
    Create a virtual DOM node (hyperscript helper).

    This is similar to React.createElement or h() in other frameworks.

    Args:
        type: The element type or component.
        *children: Child elements.
        key: Optional key for reconciliation.
        **props: Element properties.

    Returns:
        A new VNode.
    """
    return create_vnode(type, *children, key=key, **props)


# Fragment support
class Fragment:
    """Fragment component for grouping children without a wrapper."""

    pass


def fragment(*children: Union[VNode, str, None]) -> VNode:
    """Create a fragment containing children."""
    return create_vnode(Fragment, *children)
