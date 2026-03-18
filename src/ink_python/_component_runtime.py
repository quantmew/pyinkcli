"""
Internal component runtime for ink-python.

This module holds the actual element/component implementation.
Public compatibility imports remain in `component.py`.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Union


class _Element:
    __slots__ = ("type", "props", "children", "key")
    pass


RenderableNode = Union["_Element", str, None]


def _normalize_props(props: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return props or {}


def _create_element_record(
    type: Union[str, Callable, type],
    props: Optional[Dict[str, Any]],
    children: List[RenderableNode],
    key: Optional[str],
) -> "_Element":
    element = object.__new__(_Element)
    element.type = type
    element.props = _normalize_props(props)
    element.children = children
    element.key = key
    return element


def _is_element_record(value: Any) -> bool:
    return isinstance(value, _Element)


def _is_renderable_node(value: Any) -> bool:
    return _is_element_record(value) or isinstance(value, str)


def _is_text_renderable(value: Any) -> bool:
    return isinstance(value, str)


def _is_render_component_passthrough(value: Any) -> bool:
    return _is_text_renderable(value) or isElement(value)


def _normalize_child(child: Any) -> RenderableNode:
    if child is None:
        return None
    if _is_renderable_node(child):
        return child
    return str(child)


def _normalize_children(children: Any) -> List[RenderableNode]:
    processed_children: List[RenderableNode] = []
    for child in children:
        if isinstance(child, (list, tuple)):
            for subchild in child:
                normalized = _normalize_child(subchild)
                if normalized is not None:
                    processed_children.append(normalized)
            continue

        normalized = _normalize_child(child)
        if normalized is not None:
            processed_children.append(normalized)

    return processed_children


def _coerce_render_result(result: Any) -> RenderableNode:
    if _is_renderable_node(result):
        return result
    if result is None:
        return None
    return str(result)


def _is_component_instance(value: Any) -> bool:
    return isinstance(value, _Component)


def _invoke_component(
    component: Callable,
    children: tuple[RenderableNode, ...],
    props: Dict[str, Any],
) -> Any:
    return component(*children, **props)


def createElement(
    type: Union[str, Callable, type],
    *children: RenderableNode,
    key: Optional[str] = None,
    **props: Any,
) -> RenderableNode:
    return _create_element_record(
        type=type,
        props=props,
        children=_normalize_children(children),
        key=key,
    )


class _Component:
    def __init__(self, **props: Any):
        self.props = props
        self.state: Dict[str, Any] = {}
        self._state_version = 0

    def render(self) -> RenderableNode:
        return None

    def set_state(self, **kwargs: Any) -> None:
        self.state.update(kwargs)
        self._state_version += 1


def component(
    func: Optional[Callable] = None, *, name: Optional[str] = None
) -> Callable:
    def wrapper(fn: Callable) -> Callable:
        fn._is_component = True
        fn._component_name = name or fn.__name__
        return fn

    if func is not None:
        return wrapper(func)
    return wrapper


def is_component(obj: Any) -> bool:
    return callable(obj) and obj is not _Fragment


def isElement(obj: Any) -> bool:
    return _is_element_record(obj)


def renderComponent(
    component: Union[Callable, _Component, RenderableNode],
    *children: RenderableNode,
    **props: Any,
) -> RenderableNode:
    if component is None:
        return None

    if _is_render_component_passthrough(component):
        return component

    if _is_component_instance(component):
        return component.render()

    if callable(component):
        return _coerce_render_result(_invoke_component(component, children, props))

    return str(component)


class _Fragment:
    pass


def _fragment(*children: RenderableNode) -> RenderableNode:
    return createElement(_Fragment, *children)


__all__ = ["createElement", "component", "isElement", "RenderableNode"]
