"""Compatibility facade for the internal hooks runtime."""

from pyinkcli.hooks import _runtime
from pyinkcli.packages.react.ReactHooks import (
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
from pyinkcli.packages.react.dispatcher import (
    beginComponentRender as _begin_component_render,
    consumePendingRerenderPriority as _consume_pending_rerender_priority,
    endComponentRender as _end_component_render,
    resetHookState as _reset_hook_state,
    setScheduleUpdateCallback as _set_schedule_update_callback,
)

_clear_hook_state = _runtime._clear_hook_state
_finish_hook_state = _runtime._finish_hook_state
_set_rerender_callback = _runtime._set_rerender_callback

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
