"""Compatibility facade for the internal hooks runtime."""

from pyinkcli.hooks import _runtime
from pyinkcli.hooks._runtime import (
    Ref,
    useCallback,
    useEffect,
    useMemo,
    useReducer,
    useRef,
    useState,
)

_begin_component_render = _runtime._begin_component_render
_clear_hook_state = _runtime._clear_hook_state
_consume_pending_rerender_priority = _runtime._consume_pending_rerender_priority
_end_component_render = _runtime._end_component_render
_finish_hook_state = _runtime._finish_hook_state
_reset_hook_state = _runtime._reset_hook_state
_set_rerender_callback = _runtime._set_rerender_callback

__all__ = [
    "useState",
    "useEffect",
    "useRef",
    "useMemo",
    "useCallback",
    "useReducer",
    "Ref",
]
