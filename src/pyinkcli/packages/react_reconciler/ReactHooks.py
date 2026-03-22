"""Public hook compatibility surface."""

from __future__ import annotations

from pyinkcli.packages.react_reconciler.ReactFiberBeginWork import (
    checkIfWorkInProgressReceivedUpdate,
    markWorkInProgressReceivedUpdate,
)
from pyinkcli.packages.react_reconciler.ReactFiberNewContext import (
    checkIfContextChanged,
    finishReadingContext,
    prepareToReadContext,
)
from pyinkcli.packages.react_reconciler.ReactSharedInternals import shared_internals
from pyinkcli.hooks._runtime import (
    HookHasEffect,
    HookInsertion,
    HookLayout,
    HookPassive,
    Ref,
    useCallback,
    useEffect,
    useInsertionEffect,
    useLayoutEffect,
    useMemo,
    useReducer,
    useRef,
    useState,
    useTransition,
)

HooksDispatcherOnMount = object()
HooksDispatcherOnUpdate = object()
_previous_dispatcher = None


def renderWithHooks(fiber, component, *args, **kwargs):
    global _previous_dispatcher
    _previous_dispatcher = shared_internals.H
    alternate = getattr(fiber, "alternate", None)
    shared_internals.H = HooksDispatcherOnUpdate if alternate is not None else HooksDispatcherOnMount
    pending_props = getattr(fiber, "pending_props", None)
    memoized_props = getattr(fiber, "memoized_props", None)
    if pending_props != memoized_props:
        markWorkInProgressReceivedUpdate()
    try:
        prepareToReadContext(fiber)
        return component(*args, **kwargs)
    finally:
        previous_dependencies = getattr(alternate, "dependencies", []) if alternate is not None else []
        if previous_dependencies and checkIfContextChanged(previous_dependencies):
            markWorkInProgressReceivedUpdate()
            fiber.dependencies = [
                (context, getattr(context, "_currentValue", getattr(context, "_current_value", getattr(context, "_default_value", None))))
                for context, _value in previous_dependencies
            ]
        finishReadingContext()


def finishRenderingHooks() -> None:
    global _previous_dispatcher
    shared_internals.H = _previous_dispatcher


__all__ = [
    "HookHasEffect",
    "HookInsertion",
    "HookLayout",
    "HookPassive",
    "HooksDispatcherOnMount",
    "HooksDispatcherOnUpdate",
    "Ref",
    "renderWithHooks",
    "finishRenderingHooks",
    "checkIfWorkInProgressReceivedUpdate",
    "useState",
    "useEffect",
    "useInsertionEffect",
    "useLayoutEffect",
    "useRef",
    "useMemo",
    "useCallback",
    "useReducer",
    "useTransition",
]
