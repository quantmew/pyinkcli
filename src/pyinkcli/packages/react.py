from __future__ import annotations

from itertools import count

from ..component import RenderableNode, createElement, isElement
from ..hooks import _runtime as hooks_runtime
from .react_children import create_children_api
from .react_component import Component
from .react_context import ReactSharedInternals, createContext, useContext
from .react_types import forwardRef, lazy, memo

Fragment = object()


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

def _identity(value):
    return value


_id_counter = count(1)


def useId() -> str:
    return f":r{next(_id_counter)}:"


def startTransition(callback) -> None:
    callback()


def useDeferredValue(value):
    return value


Children = create_children_api()


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
