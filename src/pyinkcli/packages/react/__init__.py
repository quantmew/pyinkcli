"""React-compatible package facade translated to Python."""

from pyinkcli._component_runtime import _Fragment as Fragment
from pyinkcli.packages.react.ReactBaseClasses import Component, PureComponent, Ref, createRef
from pyinkcli.packages.react.ReactChildren import Children, count, forEach, map, only, toArray
from pyinkcli.packages.react.ReactContext import ReactContext, createContext
from pyinkcli.packages.react.ReactForwardRef import forwardRef
from pyinkcli.packages.react.ReactHooks import (
    getCacheForType,
    use,
    useActionState,
    useCacheRefresh,
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
    useMemoCache,
    useOptimistic,
    useReducer,
    useRef,
    useState,
    useSyncExternalStore,
    useTransition,
)
from pyinkcli.packages.react.ReactLazy import lazy
from pyinkcli.packages.react.ReactMemo import memo
from pyinkcli.packages.react.ReactSharedInternals import ReactSharedInternals, shared_internals
from pyinkcli.packages.react.jsx.ReactJSXElement import (
    cloneAndReplaceKey,
    cloneElement,
    createElement,
    isValidElement,
)
from pyinkcli.packages.shared.ReactVersion import version

__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE = ReactSharedInternals

__all__ = [
    "Children",
    "Component",
    "PureComponent",
    "ReactContext",
    "ReactSharedInternals",
    "__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE",
    "Fragment",
    "Ref",
    "cloneAndReplaceKey",
    "cloneElement",
    "count",
    "createContext",
    "createElement",
    "createRef",
    "forwardRef",
    "getCacheForType",
    "isValidElement",
    "lazy",
    "map",
    "memo",
    "only",
    "forEach",
    "toArray",
    "shared_internals",
    "use",
    "useActionState",
    "useCacheRefresh",
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
    "useMemoCache",
    "useOptimistic",
    "useReducer",
    "useRef",
    "useState",
    "useSyncExternalStore",
    "useTransition",
    "version",
]
