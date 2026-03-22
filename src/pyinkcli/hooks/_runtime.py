from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

HookHasEffect = 1
HookInsertion = 2
HookLayout = 4
HookPassive = 8


@dataclass
class _Ref:
    current: Any


@dataclass
class _EffectRecord:
    kind: str
    callback: Any
    deps: tuple[Any, ...] | None
    cleanup: Any = None
    needs_run: bool = True


@dataclass
class EffectInstance:
    destroy: Any = None


@dataclass
class EffectRecord:
    tag: int
    create: Any
    deps: tuple[Any, ...] | None
    inst: EffectInstance
    next: "EffectRecord | None" = None


@dataclass
class FunctionComponentUpdateQueue:
    last_effect: EffectRecord | None = None


@dataclass
class HookNode:
    index: int
    kind: str
    cleanup: Any = None


@dataclass
class HookFiber:
    component_id: str
    element_type: str
    update_queue: FunctionComponentUpdateQueue | None = None
    hook_head: HookNode | None = None


@dataclass
class _ComponentState:
    hooks: list[Any]
    cursor: int = 0
    seen: bool = False
    component_type: Any = None


_hook_state: dict[str, _ComponentState] = {}
_current_component_id: str | None = None
_current_hook_index = 0
_rerender_callback = None
_schedule_update_callback = None
_rendering = False
_pending_rerender_priority: str | None = None
_current_context_values: dict[int, list[Any]] = {}
_batched_mode: str | None = None
_batched_pending = False
_auto_batch_timer: threading.Timer | None = None
_active_component_ids: set[str] = set()
_dirty_components: set[str] = set()
_render_phase_rerender_count = 0
_runtime = SimpleNamespace(
    fibers={},
    pending_passive_unmount_fibers=[],
)


def _clear_hook_state() -> None:
    global _hook_state, _render_phase_rerender_count
    for state in _hook_state.values():
        for hook in state.hooks:
            if isinstance(hook, _EffectRecord) and hook.cleanup:
                hook.cleanup()
    _hook_state = {}
    _active_component_ids.clear()
    _dirty_components.clear()
    _render_phase_rerender_count = 0
    _runtime.fibers = {}
    _runtime.pending_passive_unmount_fibers = []


def _reset_hook_state() -> None:
    for state in _hook_state.values():
        state.seen = False


def _begin_component_render(instance_id: str, component_type: Any = None) -> None:
    global _current_component_id, _current_hook_index, _rendering
    _current_component_id = instance_id
    _current_hook_index = 0
    _rendering = True
    state = _hook_state.setdefault(instance_id, _ComponentState(hooks=[]))
    if component_type is not None and state.component_type is not None and state.component_type is not component_type:
        state.hooks = []
    if component_type is not None:
        state.component_type = component_type
    _dirty_components.discard(instance_id)
    state.cursor = 0
    state.seen = True
    _active_component_ids.add(instance_id)


def _end_component_render() -> None:
    global _current_component_id, _rendering
    _current_component_id = None
    _rendering = False


def _finish_hook_state() -> None:
    global _render_phase_rerender_count
    unseen = [instance_id for instance_id, state in _hook_state.items() if not state.seen]
    for instance_id in unseen:
        state = _hook_state.pop(instance_id)
        for hook in state.hooks:
            if isinstance(hook, _EffectRecord) and hook.cleanup:
                _runtime.pending_passive_unmount_fibers.append(
                    HookFiber(
                        component_id=instance_id,
                        element_type=instance_id,
                        hook_head=HookNode(index=0, kind="Effect", cleanup=hook.cleanup),
                    )
                )
    for state in _hook_state.values():
        for hook in state.hooks:
            if isinstance(hook, _EffectRecord) and hook.needs_run:
                if hook.cleanup:
                    hook.cleanup()
                hook.cleanup = hook.callback() if callable(hook.callback) else None
                hook.needs_run = False
    if _render_phase_rerender_count and _rerender_callback:
        count = _render_phase_rerender_count
        _render_phase_rerender_count = 0
        for _ in range(count):
            _rerender_callback()


def _set_rerender_callback(callback) -> None:
    global _rerender_callback
    _rerender_callback = callback


def _set_schedule_update_callback(callback) -> None:
    global _schedule_update_callback
    _schedule_update_callback = callback


def _consume_pending_rerender_priority() -> str | None:
    global _pending_rerender_priority
    value = _pending_rerender_priority
    _pending_rerender_priority = None
    return value


def _schedule_rerender(priority: str) -> None:
    global _pending_rerender_priority, _batched_pending, _auto_batch_timer, _render_phase_rerender_count
    _pending_rerender_priority = priority
    if _rendering:
        _render_phase_rerender_count += 1
        return
    if _batched_mode is not None:
        _batched_pending = True
        return
    if _schedule_update_callback:
        if _auto_batch_timer is None:
            _auto_batch_timer = threading.Timer(0, lambda: (_schedule_update_callback(_current_component_id, priority), _clear_auto_batch()))
            _auto_batch_timer.start()
        return
    if _auto_batch_timer is None:
        _auto_batch_timer = threading.Timer(0, lambda: (_rerender_callback and _rerender_callback(), _clear_auto_batch()))
        _auto_batch_timer.start()


def _clear_auto_batch() -> None:
    global _auto_batch_timer
    _auto_batch_timer = None


@contextmanager
def _with_batch(priority: str):
    global _batched_mode, _batched_pending, _pending_rerender_priority
    previous = _batched_mode
    _batched_mode = priority
    _batched_pending = False
    try:
        yield
    finally:
        _batched_mode = previous
        if _batched_pending:
            _pending_rerender_priority = priority
            if _rerender_callback:
                _rerender_callback()


def _batched_updates_runtime(callback):
    with _with_batch("default"):
        return callback()


def _discrete_updates_runtime(callback):
    with _with_batch("discrete"):
        return callback()


def _get_slot(initial_factory):
    if _current_component_id is None:
        raise RuntimeError("hooks can only be used while rendering")
    state = _hook_state.setdefault(_current_component_id, _ComponentState(hooks=[]))
    index = state.cursor
    if index == len(state.hooks):
        state.hooks.append(initial_factory())
    slot = state.hooks[index]
    state.cursor += 1
    return slot, index, state


def useState(initial):
    slot, index, state = _get_slot(lambda: initial() if callable(initial) else initial)
    component_id = _current_component_id

    def set_value(next_value):
        state.hooks[index] = next_value(state.hooks[index]) if callable(next_value) else next_value
        if component_id is not None:
            _dirty_components.add(component_id)
        _schedule_rerender("render_phase" if _rendering else "default")

    return slot, set_value


def useReducer(reducer, initial_arg, initializer=None):
    initial = initializer(initial_arg) if initializer else initial_arg
    value, set_value = useState(initial)

    def dispatch(action):
        set_value(lambda previous: reducer(previous, action))

    return value, dispatch


def useRef(initial):
    slot, _, _ = _get_slot(lambda: _Ref(initial))
    return slot


def useMemo(factory, deps=None):
    deps_tuple = None if deps is None else tuple(deps)

    def initial():
        return {"deps": deps_tuple, "value": factory()}

    slot, index, state = _get_slot(initial)
    if deps_tuple is None or slot["deps"] != deps_tuple:
        state.hooks[index] = {"deps": deps_tuple, "value": factory()}
        slot = state.hooks[index]
    return slot["value"]


def useCallback(callback, deps=None):
    return useMemo(lambda: callback, deps)


def _effect(kind: str, callback, deps=None):
    deps_tuple = None if deps is None else tuple(deps)

    def initial():
        return _EffectRecord(kind=kind, callback=callback, deps=deps_tuple)

    slot, index, state = _get_slot(initial)
    if slot.deps is None or deps_tuple is None or slot.deps != deps_tuple:
        slot.callback = callback
        slot.deps = deps_tuple
        slot.needs_run = True
        state.hooks[index] = slot


def useEffect(callback, deps=None):
    _effect("effect", callback, deps)


def useLayoutEffect(callback, deps=None):
    _effect("layout", callback, deps)


def useInsertionEffect(callback, deps=None):
    _effect("insertion", callback, deps)


def useTransition():
    from .use_app import useApp

    app = useApp()
    if app is None or not getattr(getattr(app, "options", None), "concurrent", False):
        return False, lambda callback: callback()

    def start_transition(callback):
        app._transition_pending = True
        _schedule_rerender("transition")

        def run():
            callback()
            app._transition_pending = False
            _schedule_rerender("default")

        app._schedule_transition(run, delay=0.08)

    return bool(getattr(app, "_transition_pending", False)), start_transition


def useContext(context):
    stack = _current_context_values.get(id(context))
    if stack:
        return stack[-1]
    return getattr(context, "current_value", context.default_value)


@contextmanager
def _push_context(context, value):
    stack = _current_context_values.setdefault(id(context), [])
    stack.append(value)
    try:
        yield
    finally:
        stack.pop()


__all__ = [
    "EffectInstance",
    "EffectRecord",
    "FunctionComponentUpdateQueue",
    "HookFiber",
    "HookHasEffect",
    "HookInsertion",
    "HookLayout",
    "HookNode",
    "HookPassive",
    "_Ref",
    "_batched_updates_runtime",
    "_begin_component_render",
    "_clear_hook_state",
    "_consume_pending_rerender_priority",
    "_discrete_updates_runtime",
    "_end_component_render",
    "_finish_hook_state",
    "_push_context",
    "_reset_hook_state",
    "_set_rerender_callback",
    "_set_schedule_update_callback",
    "useCallback",
    "useContext",
    "useEffect",
    "useInsertionEffect",
    "useLayoutEffect",
    "useMemo",
    "useReducer",
    "useRef",
    "useState",
    "useTransition",
]


def _get_passive_queue_state():
    return {
        "has_deferred_passive_work": bool(_runtime.fibers),
        "pending_passive_unmount_fibers": len(_runtime.pending_passive_unmount_fibers),
    }


def _component_can_bail_out(instance_id: str) -> bool:
    if instance_id in _dirty_components:
        return False
    state = _hook_state.get(instance_id)
    if state is None:
        return True
    for hook in state.hooks:
        if isinstance(hook, _EffectRecord) and hook.deps is None:
            return False
    return True
