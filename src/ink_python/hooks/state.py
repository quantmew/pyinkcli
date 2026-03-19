"""Compatibility facade for the internal hooks runtime."""

from ink_python.hooks._runtime import (
    Ref,
    _begin_component_render,
    _clear_hook_state,
    _consume_pending_rerender_priority,
    _discrete_updates_runtime,
    _batched_updates_runtime,
    _end_component_render,
    _finish_hook_state,
    _reset_hook_state,
    _set_rerender_callback,
    useCallback,
    useEffect,
    useMemo,
    useReducer,
    useRef,
    useState,
)

__all__ = [
    "useState",
    "useEffect",
    "useRef",
    "useMemo",
    "useCallback",
    "useReducer",
    "Ref",
    "_begin_component_render",
    "_clear_hook_state",
    "_consume_pending_rerender_priority",
    "_discrete_updates_runtime",
    "_batched_updates_runtime",
    "_end_component_render",
    "_finish_hook_state",
    "_reset_hook_state",
    "_set_rerender_callback",
]
