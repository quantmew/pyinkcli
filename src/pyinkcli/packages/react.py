from __future__ import annotations

from dataclasses import dataclass
from itertools import count
from types import SimpleNamespace
from typing import Any

from ..component import RenderableNode, createElement, isElement
from ..hooks import _runtime as hooks_runtime

Fragment = object()


class _SharedInternals(SimpleNamespace):
    H: Any = None


ReactSharedInternals = _SharedInternals()


class Component:
    def __init__(self, props: dict[str, Any] | None = None, context: Any = None, updater: Any = None) -> None:
        self.props = props or {}
        self.context = context
        self.refs = {}
        self.state = {}
        self.updater = updater or _NoopUpdater()

    def setState(self, partial_state, callback=None) -> None:
        if partial_state is not None and not callable(partial_state) and not isinstance(partial_state, dict):
            raise TypeError("setState(...) takes an object of state variables to update")
        self.updater.enqueueSetState(self, partial_state, callback, "setState")

    def forceUpdate(self, callback=None) -> None:
        self.updater.enqueueForceUpdate(self, callback, "forceUpdate")


class _NoopUpdater:
    def enqueueSetState(self, public_instance, partial_state, callback=None, callerName=None):
        if callable(partial_state):
            partial_state = partial_state(public_instance.state, public_instance.props)
        if isinstance(partial_state, dict):
            public_instance.state.update(partial_state)
        if callback:
            callback()

    def enqueueForceUpdate(self, public_instance, callback=None, callerName=None):
        if callback:
            callback()


@dataclass
class _Context:
    default_value: Any
    current_value: Any
    Provider: Any = None
    Consumer: Any = None


class _ProviderType:
    __ink_react_provider__ = True

    def __init__(self, context: _Context) -> None:
        self._context = context


class _ConsumerType:
    __ink_react_consumer__ = True

    def __init__(self, context: _Context) -> None:
        self._context = context


def createContext(default_value: Any) -> _Context:
    context = _Context(default_value=default_value, current_value=default_value)
    context.Provider = _ProviderType(context)
    context.Consumer = _ConsumerType(context)
    return context


def useContext(context: _Context) -> Any:
    return hooks_runtime.useContext(context)


def cloneElement(element: RenderableNode, *children: Any, **props: Any) -> RenderableNode:
    next_props = dict(element.props)
    next_props.update(props)
    next_key = next_props.pop("key", element.key)
    return RenderableNode(
        type=element.type,
        props=next_props,
        children=element.children if not children else list(children),
        key=next_key,
    )


class _MemoType:
    __ink_react_memo__ = True

    def __init__(self, type_: Any) -> None:
        self.type = type_


def memo(type_: Any) -> _MemoType:
    return _MemoType(type_)


class _ForwardRefType:
    __ink_react_forward_ref__ = True

    def __init__(self, render) -> None:
        self.render = render


def forwardRef(render) -> _ForwardRefType:
    return _ForwardRefType(render)


class _LazyType:
    __ink_react_lazy__ = True

    def __init__(self, factory) -> None:
        self._factory = factory
        self._payload = None

    def _init(self, payload=None):
        if self._payload is None:
            self._payload = self._factory()
        return self._payload["default"]


def lazy(factory) -> _LazyType:
    return _LazyType(factory)


def _identity(value):
    return value


_id_counter = count(1)


def useId() -> str:
    return f":r{next(_id_counter)}:"


def startTransition(callback) -> None:
    callback()


def useDeferredValue(value):
    return value


Children = {
    "toArray": lambda children: _children_to_array(children),
    "map": lambda children, fn: [fn(child, index) for index, child in enumerate(_children_to_array(children))],
    "count": lambda children: len(_children_to_array(children, keep_primitives=True)),
    "only": lambda child: child,
}


def _child_key_prefix(base: str, child: Any) -> str:
    if isElement(child) and child.key is not None:
        return f"{base}:$%s" % child.key if base else f".$%s" % child.key
    return base


def _children_to_array(children: Any, *, keep_primitives: bool = False, prefix: str = "") -> list[Any]:
    result: list[Any] = []
    if children is None:
        return result
    if isinstance(children, (list, tuple)):
        for index, child in enumerate(children):
            next_prefix = f"{prefix}.{index}" if not prefix else f"{prefix}:{index}"
            result.extend(_children_to_array(child, keep_primitives=keep_primitives, prefix=next_prefix))
        return result
    if isElement(children):
        computed_key = _child_key_prefix(prefix or ".", children)
        if prefix and computed_key == prefix:
            computed_key = prefix
        elif not prefix and children.key is None:
            computed_key = ".0"
        if children.key is not None and prefix:
            computed_key = f"{prefix}:$%s" % children.key
        elif children.key is None and prefix:
            computed_key = prefix
        elif children.key is not None:
            computed_key = f".$%s" % children.key
        result.append(cloneElement(children, key=computed_key))
        return result
    if keep_primitives:
        result.append(children)
    return result


useState = hooks_runtime.useState
useEffect = hooks_runtime.useEffect
useLayoutEffect = hooks_runtime.useLayoutEffect
useMemo = hooks_runtime.useMemo
useRef = hooks_runtime.useRef
useReducer = hooks_runtime.useReducer
useCallback = hooks_runtime.useCallback

__all__ = [
    "Children",
    "Component",
    "Fragment",
    "ReactSharedInternals",
    "cloneElement",
    "createContext",
    "createElement",
    "forwardRef",
    "isValidElement",
    "lazy",
    "memo",
    "startTransition",
    "useCallback",
    "useContext",
    "useDeferredValue",
    "useEffect",
    "useId",
    "useLayoutEffect",
    "useMemo",
    "useReducer",
    "useRef",
    "useState",
]

isValidElement = isElement

