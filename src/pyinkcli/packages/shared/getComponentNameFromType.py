"""Best-effort component name helper."""

from __future__ import annotations

from typing import Any

from pyinkcli.packages.shared.ReactFeatureFlags import (
    enableTransitionTracing,
    enableViewTransition,
)
from pyinkcli.packages.shared.ReactSymbols import (
    REACT_ACTIVITY_TYPE,
    REACT_CONSUMER_TYPE,
    REACT_CONTEXT_TYPE,
    REACT_FORWARD_REF_TYPE,
    REACT_FRAGMENT_TYPE,
    REACT_LAZY_TYPE,
    REACT_MEMO_TYPE,
    REACT_PORTAL_TYPE,
    REACT_PROFILER_TYPE,
    REACT_STRICT_MODE_TYPE,
    REACT_SUSPENSE_LIST_TYPE,
    REACT_SUSPENSE_TYPE,
    REACT_TRACING_MARKER_TYPE,
    REACT_VIEW_TRANSITION_TYPE,
)


def getComponentNameFromType(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value

    type_tag = getattr(value, "$$typeof", None)
    if getattr(value, "__ink_react_provider__", False):
        context = getattr(value, "_context", value)
        context_name = getattr(context, "displayName", None) or "Context"
        return f"{context_name}.Provider"
    if getattr(value, "__ink_react_consumer__", False):
        context = getattr(value, "_context", value)
        context_name = getattr(context, "displayName", None) or "Context"
        return f"{context_name}.Consumer"
    if getattr(value, "__ink_react_forward_ref__", False):
        render = getattr(value, "render", None)
        inner_name = getattr(render, "displayName", None) or getattr(render, "__name__", "")
        return f"ForwardRef({inner_name})" if inner_name else "ForwardRef"
    if getattr(value, "__ink_react_memo__", False):
        outer_name = getattr(value, "displayName", None)
        if outer_name:
            return outer_name
        return getComponentNameFromType(getattr(value, "type", None)) or "Memo"
    if getattr(value, "__ink_react_lazy__", False):
        init = getattr(value, "_init", None)
        payload = getattr(value, "_payload", None)
        if callable(init):
            try:
                return getComponentNameFromType(init(payload))
            except Exception:
                return None

    for attr in ("displayName", "__name__", "name"):
        name = getattr(value, attr, None)
        if isinstance(name, str) and name:
            return name

    if value is REACT_FRAGMENT_TYPE:
        return "Fragment"
    if value is REACT_PROFILER_TYPE:
        return "Profiler"
    if value is REACT_STRICT_MODE_TYPE:
        return "StrictMode"
    if value is REACT_SUSPENSE_TYPE:
        return "Suspense"
    if value is REACT_SUSPENSE_LIST_TYPE:
        return "SuspenseList"
    if value is REACT_ACTIVITY_TYPE:
        return "Activity"
    if value is REACT_VIEW_TRANSITION_TYPE and enableViewTransition:
        return "ViewTransition"
    if value is REACT_TRACING_MARKER_TYPE and enableTransitionTracing:
        return "TracingMarker"

    if type_tag is REACT_PORTAL_TYPE:
        return "Portal"
    if type_tag is REACT_CONTEXT_TYPE:
        return getattr(value, "displayName", None) or "Context"
    if type_tag is REACT_CONSUMER_TYPE:
        context = getattr(value, "_context", value)
        context_name = getattr(context, "displayName", None) or "Context"
        return f"{context_name}.Consumer"
    if type_tag is REACT_FORWARD_REF_TYPE:
        render = getattr(value, "render", None)
        inner_name = getattr(render, "displayName", None) or getattr(render, "__name__", "")
        if inner_name:
            return f"ForwardRef({inner_name})"
        return "ForwardRef"
    if type_tag is REACT_MEMO_TYPE:
        outer_name = getattr(value, "displayName", None)
        if outer_name:
            return outer_name
        return getComponentNameFromType(getattr(value, "type", None)) or "Memo"
    if type_tag is REACT_LAZY_TYPE:
        init = getattr(value, "_init", None)
        payload = getattr(value, "_payload", None)
        if callable(init):
            try:
                return getComponentNameFromType(init(payload))
            except Exception:
                return None

    return None


__all__ = ["getComponentNameFromType"]
