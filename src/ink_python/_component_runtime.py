"""
Internal component runtime for ink-python.

This module holds the actual element/component implementation.
Public compatibility imports remain in `component.py`.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any, Callable, Dict, List, Optional, Union


class _Element:
    __slots__ = ("type", "props", "children", "key")
    pass


class _ScopedNode:
    __slots__ = ("node", "context_manager_factories")

    def __getattr__(self, name: str) -> Any:
        return getattr(self.node, name)


RenderableNode = Union["_Element", "_ScopedNode", str, None]


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


def _is_scoped_node(value: Any) -> bool:
    return isinstance(value, _ScopedNode)


def _is_renderable_node(value: Any) -> bool:
    return _is_element_record(value) or _is_scoped_node(value) or isinstance(value, str)


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
    if _is_component_instance(result):
        return _coerce_render_result(result.render())
    if _is_renderable_node(result):
        return result
    if result is None:
        return None
    return str(result)


def _is_component_instance(value: Any) -> bool:
    return isinstance(value, _Component)


def _is_component_class(value: Any) -> bool:
    return isinstance(value, type) and issubclass(value, _Component)


def _coalesce_component_children(
    children: tuple[RenderableNode, ...],
) -> RenderableNode:
    normalized_children = _normalize_children(children)
    if not normalized_children:
        return None
    if len(normalized_children) == 1:
        return normalized_children[0]
    return _fragment(*normalized_children)


def _merge_component_props(
    children: tuple[RenderableNode, ...],
    props: Dict[str, Any],
) -> Dict[str, Any]:
    merged_props = dict(props)
    if "children" not in merged_props:
        merged_props["children"] = _coalesce_component_children(children)
    return merged_props


def _create_component_instance(
    component: type["_Component"],
    children: tuple[RenderableNode, ...],
    props: Dict[str, Any],
) -> "_Component":
    return component(**_merge_component_props(children, props))


def _invoke_component(
    component: Callable,
    children: tuple[RenderableNode, ...],
    props: Dict[str, Any],
) -> Any:
    if _is_component_class(component):
        instance = _create_component_instance(component, children, props)
        return instance.render()
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


def scopeRender(
    node: RenderableNode,
    *context_manager_factories: Callable[[], AbstractContextManager[Any]],
) -> RenderableNode:
    scoped = object.__new__(_ScopedNode)
    scoped.node = node
    scoped.context_manager_factories = tuple(context_manager_factories)
    return scoped


class _Component:
    def __init__(self, **props: Any):
        self.props = props
        self.state: Dict[str, Any] = {}
        self._state_version = 0
        self._is_unmounted = False
        self._is_mounted = False
        self._last_rendered_node: RenderableNode = None
        self._pending_previous_state: Optional[Dict[str, Any]] = None
        self._nearest_error_boundary: Optional["_Component"] = None

    def render(self) -> RenderableNode:
        return None

    def set_state(
        self,
        update: Optional[
            Union[
                Dict[str, Any],
                Callable[[Dict[str, Any], Dict[str, Any]], Optional[Dict[str, Any]]],
            ]
        ] = None,
        **kwargs: Any,
    ) -> None:
        if self._is_unmounted:
            return

        partial_state: Dict[str, Any] = {}
        if callable(update):
            computed = update(dict(self.state), dict(self.props))
            if isinstance(computed, dict):
                partial_state.update(computed)
        elif isinstance(update, dict):
            partial_state.update(update)

        if kwargs:
            partial_state.update(kwargs)

        if not partial_state:
            return

        if self._pending_previous_state is None:
            self._pending_previous_state = dict(self.state)
        self.state.update(partial_state)
        self._state_version += 1
        from ink_python.hooks._runtime import _request_rerender

        _request_rerender()

    def force_update(self) -> None:
        if self._is_unmounted:
            return
        from ink_python.hooks._runtime import _request_rerender

        _request_rerender()


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
    return _is_element_record(obj) or _is_scoped_node(obj)


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
        return _coerce_render_result(component.render())

    if _is_component_class(component):
        instance = _create_component_instance(component, children, props)
        return _coerce_render_result(instance.render())

    if callable(component):
        return _coerce_render_result(_invoke_component(component, children, props))

    return str(component)


class _Fragment:
    pass


def _fragment(*children: RenderableNode) -> RenderableNode:
    return createElement(_Fragment, *children)


__all__ = ["createElement", "component", "isElement", "RenderableNode", "scopeRender"]
