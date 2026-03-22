"""
Internal component runtime for pyinkcli.

This module holds the actual element/component implementation.
Public compatibility imports remain in `component.py`.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any, Union


class _Element:
    __slots__ = ("type", "props", "children", "key")
    pass


class _ScopedNode:
    __slots__ = ("node", "context_manager_factories")

    def __getattr__(self, name: str) -> Any:
        return getattr(self.node, name)


RenderableNode = Union["_Element", "_ScopedNode", str, None]


def _normalize_props(props: dict[str, Any] | None) -> dict[str, Any]:
    return props or {}


def _create_element_record(
    type: str | Callable | type,
    props: dict[str, Any] | None,
    children: list[RenderableNode],
    key: str | None,
) -> _Element:
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


def _normalize_child(child: Any, *, preserve_callables: bool = False) -> RenderableNode | Any:
    if child is None:
        return None
    if preserve_callables and callable(child):
        return child
    if _is_renderable_node(child):
        return child
    return str(child)


def _normalize_children(children: Any, *, preserve_callables: bool = False) -> list[RenderableNode | Any]:
    processed_children: list[RenderableNode | Any] = []
    for child in children:
        if isinstance(child, (list, tuple)):
            for subchild in child:
                normalized = _normalize_child(subchild, preserve_callables=preserve_callables)
                if normalized is not None:
                    processed_children.append(normalized)
            continue

        normalized = _normalize_child(child, preserve_callables=preserve_callables)
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
    props: dict[str, Any],
) -> dict[str, Any]:
    merged_props = dict(props)
    if "children" not in merged_props:
        merged_props["children"] = _coalesce_component_children(children)
    return merged_props


def _create_component_instance(
    component: type[_Component],
    children: tuple[RenderableNode, ...],
    props: dict[str, Any],
) -> _Component:
    return component(**_merge_component_props(children, props))


def _invoke_component(
    component: Callable,
    children: tuple[RenderableNode, ...],
    props: dict[str, Any],
) -> Any:
    if _is_component_class(component):
        instance = _create_component_instance(component, children, props)
        return instance.render()
    return component(*children, **props)


def createElement(
    type: str | Callable | type,
    *children: RenderableNode,
    key: str | None = None,
    **props: Any,
) -> RenderableNode:
    preserve_callables = bool(getattr(type, "__ink_react_consumer__", False))
    return _create_element_record(
        type=type,
        props=props,
        children=_normalize_children(children, preserve_callables=preserve_callables),
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
        self.state: dict[str, Any] = {}
        self.refs: dict[str, Any] = {}
        self.updater: Any = None
        self._state_version = 0
        self._is_unmounted = False
        self._is_mounted = False
        self._last_rendered_node: RenderableNode = None
        self._pending_previous_state: dict[str, Any] | None = None
        self._nearest_error_boundary: _Component | None = None
        self._react_update_callbacks: list[Callable[[], Any]] = []

    def render(self) -> RenderableNode:
        return None

    def set_state(
        self,
        update: dict[str, Any] | Callable[[dict[str, Any], dict[str, Any]], dict[str, Any] | None] | None = None,
        **kwargs: Any,
    ) -> None:
        updater = getattr(self, "updater", None)
        if updater is not None and hasattr(updater, "enqueueSetState"):
            payload: Any = update if update is not None else {}
            if kwargs:
                if callable(payload):
                    original = payload

                    def merged_payload(prev_state, props):
                        result = original(prev_state, props)
                        next_result = dict(result) if isinstance(result, dict) else {}
                        next_result.update(kwargs)
                        return next_result

                    payload = merged_payload
                else:
                    merged = dict(payload) if isinstance(payload, dict) else {}
                    merged.update(kwargs)
                    payload = merged
            updater.enqueueSetState(self, payload, None, "setState")
            return

        if self._is_unmounted:
            return

        partial_state: dict[str, Any] = {}
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
        from pyinkcli.packages.react.dispatcher import requestRerender

        requestRerender()

    def force_update(self) -> None:
        updater = getattr(self, "updater", None)
        if updater is not None and hasattr(updater, "enqueueForceUpdate"):
            updater.enqueueForceUpdate(self, None, "forceUpdate")
            return
        if self._is_unmounted:
            return
        from pyinkcli.packages.react.dispatcher import requestRerender

        requestRerender()


def component(
    func: Callable | None = None, *, name: str | None = None
) -> Callable:
    def wrapper(fn: Callable) -> Callable:
        fn._is_component = True
        fn._component_name = name or fn.__name__
        fn.__ink_runtime_sources__ = ("imperative_render",)
        return fn

    if func is not None:
        return wrapper(func)
    return wrapper


def is_component(obj: Any) -> bool:
    return callable(obj) and obj is not _Fragment


def isElement(obj: Any) -> bool:
    return _is_element_record(obj) or _is_scoped_node(obj)


def renderComponent(
    component: Callable | _Component | RenderableNode,
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
