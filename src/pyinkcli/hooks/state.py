"""Compatibility facade for the internal hooks runtime."""

from pyinkcli.hooks import _runtime
from pyinkcli.hooks._runtime import (
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

_begin_component_render = _runtime._begin_component_render
_clear_hook_state = _runtime._clear_hook_state
_consume_pending_rerender_priority = _runtime._consume_pending_rerender_priority
_end_component_render = _runtime._end_component_render
_finish_hook_state = _runtime._finish_hook_state
_reset_hook_state = _runtime._reset_hook_state
_set_rerender_callback = _runtime._set_rerender_callback
_set_schedule_update_callback = _runtime._set_schedule_update_callback

__all__ = [
    "useState",
    "useEffect",
    "useLayoutEffect",
    "useInsertionEffect",
    "useRef",
    "useMemo",
    "useCallback",
    "useReducer",
    "useTransition",
    "Ref",
]
