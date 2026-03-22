"""Shared React symbol constants."""

from __future__ import annotations

import builtins


class _ReactSymbol:
    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"Symbol.for({self.name!r})"


REACT_LEGACY_ELEMENT_TYPE = _ReactSymbol("react.element")
REACT_ELEMENT_TYPE = _ReactSymbol("react.transitional.element")
REACT_PORTAL_TYPE = _ReactSymbol("react.portal")
REACT_FRAGMENT_TYPE = _ReactSymbol("react.fragment")
REACT_STRICT_MODE_TYPE = _ReactSymbol("react.strict_mode")
REACT_PROFILER_TYPE = _ReactSymbol("react.profiler")
REACT_CONSUMER_TYPE = _ReactSymbol("react.consumer")
REACT_CONTEXT_TYPE = _ReactSymbol("react.context")
REACT_FORWARD_REF_TYPE = _ReactSymbol("react.forward_ref")
REACT_SUSPENSE_TYPE = _ReactSymbol("react.suspense")
REACT_SUSPENSE_LIST_TYPE = _ReactSymbol("react.suspense_list")
REACT_MEMO_TYPE = _ReactSymbol("react.memo")
REACT_LAZY_TYPE = _ReactSymbol("react.lazy")
REACT_SCOPE_TYPE = _ReactSymbol("react.scope")
REACT_ACTIVITY_TYPE = _ReactSymbol("react.activity")
REACT_LEGACY_HIDDEN_TYPE = _ReactSymbol("react.legacy_hidden")
REACT_TRACING_MARKER_TYPE = _ReactSymbol("react.tracing_marker")
REACT_MEMO_CACHE_SENTINEL = _ReactSymbol("react.memo_cache_sentinel")
REACT_VIEW_TRANSITION_TYPE = _ReactSymbol("react.view_transition")
REACT_OPTIMISTIC_KEY = _ReactSymbol("react.optimistic_key")

ASYNC_ITERATOR = getattr(builtins, "aiter", None)


def getIteratorFn(maybeIterable):
    if maybeIterable is None or isinstance(maybeIterable, (str, bytes, dict)):
        return None
    iterator = getattr(maybeIterable, "__iter__", None)
    if callable(iterator):
        return iterator
    faux = getattr(maybeIterable, "@@iterator", None)
    if callable(faux):
        return faux
    return None


__all__ = [
    "REACT_LEGACY_ELEMENT_TYPE",
    "REACT_ELEMENT_TYPE",
    "REACT_PORTAL_TYPE",
    "REACT_FRAGMENT_TYPE",
    "REACT_STRICT_MODE_TYPE",
    "REACT_PROFILER_TYPE",
    "REACT_CONSUMER_TYPE",
    "REACT_CONTEXT_TYPE",
    "REACT_FORWARD_REF_TYPE",
    "REACT_SUSPENSE_TYPE",
    "REACT_SUSPENSE_LIST_TYPE",
    "REACT_MEMO_TYPE",
    "REACT_LAZY_TYPE",
    "REACT_SCOPE_TYPE",
    "REACT_ACTIVITY_TYPE",
    "REACT_LEGACY_HIDDEN_TYPE",
    "REACT_TRACING_MARKER_TYPE",
    "REACT_MEMO_CACHE_SENTINEL",
    "REACT_VIEW_TRANSITION_TYPE",
    "REACT_OPTIMISTIC_KEY",
    "ASYNC_ITERATOR",
    "getIteratorFn",
]
