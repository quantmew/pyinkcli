"""Minimal React client compatibility surface for pyinkcli."""

from __future__ import annotations

from pyinkcli._component_runtime import _Fragment as Fragment, createElement, isElement as isValidElement
from pyinkcli.packages.react.ReactBaseClasses import Component, PureComponent
from pyinkcli.packages.react.ReactChildren import count, forEach, map, only, toArray
from pyinkcli.packages.react.ReactContext import createContext
from pyinkcli.packages.react.ReactCreateRef import createRef
from pyinkcli.packages.react.ReactForwardRef import forwardRef
from pyinkcli.packages.react.ReactHooks import (
    useCallback,
    useContext,
    useDebugValue,
    useDeferredValue,
    useEffect,
    useEffectEvent,
    useId,
    useImperativeHandle,
    useInsertionEffect,
    useLayoutEffect,
    useMemo,
    useReducer,
    useRef,
    useState,
    useSyncExternalStore,
    useTransition,
)
from pyinkcli.packages.react.ReactLazy import lazy
from pyinkcli.packages.react.ReactMemo import memo
from pyinkcli.packages.react.ReactSharedInternalsClient import ReactSharedInternals
from pyinkcli.packages.react.ReactStartTransition import startTransition

version = "0.1.1"

Children = {
    "map": map,
    "forEach": forEach,
    "count": count,
    "toArray": toArray,
    "only": only,
}


def cloneElement(element, *children, **props):
    merged_props = dict(getattr(element, "props", {}))
    merged_props.update(props)
    next_children = children if children else tuple(getattr(element, "children", ()))
    return createElement(
        getattr(element, "type", None),
        *next_children,
        key=getattr(element, "key", None),
        **merged_props,
    )


__all__ = [
    "Children",
    "Component",
    "Fragment",
    "PureComponent",
    "ReactSharedInternals",
    "cloneElement",
    "createContext",
    "createElement",
    "createRef",
    "forwardRef",
    "isValidElement",
    "lazy",
    "memo",
    "startTransition",
    "useCallback",
    "useContext",
    "useDebugValue",
    "useDeferredValue",
    "useEffect",
    "useEffectEvent",
    "useId",
    "useImperativeHandle",
    "useInsertionEffect",
    "useLayoutEffect",
    "useMemo",
    "useReducer",
    "useRef",
    "useState",
    "useSyncExternalStore",
    "useTransition",
    "version",
]
