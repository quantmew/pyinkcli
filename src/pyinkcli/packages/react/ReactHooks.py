"""React hook exports."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from itertools import count
from typing import Any

from pyinkcli.packages.react.ReactSharedInternals import shared_internals
from pyinkcli.packages.react_reconciler.ReactFiberNewContext import readContext


class Ref:
    def __init__(self, current: Any = None) -> None:
        self.current = current


_id_counter = count(1)


def _runtime():
    return importlib.import_module("pyinkcli.hooks._runtime")


def _resolve_context(context: Any) -> Any:
    return getattr(context, "_context", context)


def _context_value(context: Any) -> Any:
    resolved = _resolve_context(context)
    if resolved is None:
        return None
    return getattr(resolved, "_currentValue", getattr(resolved, "_default_value", None))


def getCacheForType(resourceType: Callable[[], Any]) -> Any:
    dispatcher = getattr(shared_internals, "A", None)
    if dispatcher is None or not hasattr(dispatcher, "getCacheForType"):
        return resourceType()
    return dispatcher.getCacheForType(resourceType)


def useContext(Context: Any) -> Any:
    dispatcher = getattr(shared_internals, "H", None)
    if dispatcher is not None and hasattr(dispatcher, "useContext"):
        return dispatcher.useContext(Context)
    return readContext(_resolve_context(Context))


def useState(initialState):
    return _runtime().useState(initialState)


def useReducer(reducer, initialArg, init=None):
    return _runtime().useReducer(reducer, initialArg, init)


def useRef(initialValue=None):
    return _runtime().useRef(initialValue)


def useEffect(create, deps=None):
    return _runtime().useEffect(create, deps)


def useInsertionEffect(create, deps=None):
    return _runtime().useInsertionEffect(create, deps)


def useLayoutEffect(create, deps=None):
    return _runtime().useLayoutEffect(create, deps)


def useCallback(callback, deps=None):
    return _runtime().useCallback(callback, deps)


def useMemo(create, deps=None):
    return _runtime().useMemo(create, deps)


def useTransition():
    return _runtime().useTransition()


def useImperativeHandle(ref, create, deps=None):
    value = create()
    if ref is None:
        return None
    if callable(ref):
        ref(value)
    else:
        ref.current = value
    return None


def useDebugValue(value, formatterFn=None):
    return None


def useDeferredValue(value, initialValue=None):
    return value


def useId() -> str:
    return f"react-{next(_id_counter)}"


def useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot=None):
    return getSnapshot()


def useCacheRefresh():
    def refresh(*args, **kwargs):
        return None

    return refresh


def use(usable):
    if callable(usable):
        return usable()
    return usable


def useMemoCache(size: int):
    return [None] * size


def useEffectEvent(callback):
    return callback


def useOptimistic(passthrough, reducer=None):
    def dispatch(action):
        if reducer is None:
            return None
        return reducer(passthrough, action)

    return passthrough, dispatch


def useActionState(action, initialState, permalink=None):
    def dispatch(payload):
        return action(initialState, payload)

    return initialState, dispatch, False


__all__ = [
    "Ref",
    "getCacheForType",
    "useContext",
    "useCallback",
    "useEffect",
    "useInsertionEffect",
    "useLayoutEffect",
    "useMemo",
    "useReducer",
    "useRef",
    "useState",
    "useTransition",
    "useImperativeHandle",
    "useDebugValue",
    "useDeferredValue",
    "useId",
    "useSyncExternalStore",
    "useCacheRefresh",
    "use",
    "useMemoCache",
    "useEffectEvent",
    "useOptimistic",
    "useActionState",
]
