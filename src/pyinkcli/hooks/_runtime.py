from __future__ import annotations

import threading
import time
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
    queued: bool = False


@dataclass
class EffectInstance:
    destroy: Any = None


@dataclass
class EffectRecord:
    tag: int
    create: Any
    deps: tuple[Any, ...] | None
    inst: EffectInstance
    next: EffectRecord | None = None


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
    context_dependent: bool = False


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
_running_effect_kind: str | None = None
_trace_callback = None
_runtime = SimpleNamespace(
    fibers={},
    pending_passive_unmount_fibers=[],
    pending_passive_mount_effects=[],
)
_suppress_immediate_passive_flush = False
_PRIORITY_ORDER = {"transition": 0, "default": 1, "discrete": 2}
_KNOWN_PRIORITIES = {"default", "discrete", "transition", "continuous", "render_phase"}


def _coerce_priority(priority: str | None) -> str:
    if priority in _KNOWN_PRIORITIES:
        return "default" if priority == "continuous" else priority
    return "default"


def _merge_priority(current: str | None, incoming: str) -> str:
    if not current:
        return incoming
    current_rank = _PRIORITY_ORDER.get(current, 1)
    incoming_rank = _PRIORITY_ORDER.get(incoming, 1)
    return current if current_rank >= incoming_rank else incoming


def _priority_from_mode(mode: str | None, requested: str) -> str:
    normalized = _coerce_priority(requested)
    if normalized == "default" and mode in _PRIORITY_ORDER:
        return mode
    return normalized


def _clear_hook_state() -> None:
    global _hook_state, _render_phase_rerender_count, _pending_rerender_priority, _auto_batch_timer, _running_effect_kind
    for state in list(_hook_state.values()):
        for hook in state.hooks:
            if isinstance(hook, _EffectRecord) and hook.cleanup:
                hook.cleanup()
    _hook_state = {}
    _active_component_ids.clear()
    _dirty_components.clear()
    _render_phase_rerender_count = 0
    _pending_rerender_priority = None
    if _auto_batch_timer is not None:
        _auto_batch_timer.cancel()
        _auto_batch_timer = None
    _runtime.fibers = {}
    _runtime.pending_passive_unmount_fibers = []
    _runtime.pending_passive_mount_effects = []
    _running_effect_kind = None


def _set_trace_callback(callback) -> None:
    global _trace_callback
    _trace_callback = callback


def _trace(event: str, **fields) -> None:
    if not _trace_callback:
        return
    try:
        _trace_callback(
            {
                "source": "hooks",
                "event": event,
                "ts": time.perf_counter_ns(),
                **fields,
            }
        )
    except Exception:
        pass


def _reset_hook_state() -> None:
    for state in _hook_state.values():
        state.seen = False


def _begin_component_render(instance_id: str, component_type: Any = None) -> None:
    global _current_component_id, _current_hook_index, _rendering
    _current_component_id = instance_id
    _current_hook_index = 0
    _rendering = True
    _trace("hooks.begin_component_render", component_id=instance_id, hook_count=len(_hook_state.get(instance_id, _ComponentState([])).hooks))
    state = _hook_state.setdefault(instance_id, _ComponentState(hooks=[]))
    if component_type is not None and state.component_type is not None and state.component_type is not component_type:
        state.hooks = []
    if component_type is not None:
        state.component_type = component_type
    _dirty_components.discard(instance_id)
    state.cursor = 0
    state.seen = True
    state.context_dependent = False
    _active_component_ids.add(instance_id)


def _end_component_render() -> None:
    global _current_component_id, _rendering
    _trace("hooks.end_component_render", component_id=_current_component_id)
    _current_component_id = None
    _rendering = False


def _finish_hook_state() -> None:
    global _render_phase_rerender_count, _running_effect_kind
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
    passive_hooks: list[_EffectRecord] = []
    for kind in ("insertion", "layout"):
        _running_effect_kind = kind
        try:
            for state in _hook_state.values():
                for hook in state.hooks:
                    if not isinstance(hook, _EffectRecord) or not hook.needs_run:
                        continue
                    if hook.kind == "effect":
                        passive_hooks.append(hook)
                        continue
                    if hook.kind != kind:
                        continue
                    if hook.cleanup:
                        hook.cleanup()
                    hook.cleanup = hook.callback() if callable(hook.callback) else None
                    hook.needs_run = False
        finally:
            _running_effect_kind = None

    if _render_phase_rerender_count and _rerender_callback:
        count = _render_phase_rerender_count
        _render_phase_rerender_count = 0
        for _ in range(count):
            _rerender_callback()
        return

    _running_effect_kind = "effect"
    try:
        for hook in passive_hooks:
            if hook.queued:
                continue
            hook.queued = True
            _runtime.pending_passive_mount_effects.append(hook)
    finally:
        _running_effect_kind = None

    if _runtime.pending_passive_mount_effects and not _suppress_immediate_passive_flush:
        from ..packages.react_reconciler.ReactFiberWorkLoop import flushPendingEffects

        flushPendingEffects()


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


def _current_render_priority(default: str = "default") -> str:
    return _priority_from_mode(_batched_mode, default)


def _schedule_rerender(priority: str) -> None:
    global _pending_rerender_priority, _batched_pending, _auto_batch_timer, _render_phase_rerender_count
    resolved_priority = _priority_from_mode(_batched_mode, priority)
    _trace(
        "hooks.schedule_rerender",
        requested_priority=priority,
        resolved_priority=resolved_priority,
        rendering=_rendering,
        batched=_batched_mode is not None,
        current_component=_current_component_id,
    )
    _pending_rerender_priority = _merge_priority(_pending_rerender_priority, resolved_priority)
    if _rendering:
        if _batched_mode is not None:
            _trace("hooks.rerender_batched", deferred=True, mode=_batched_mode)
            _batched_pending = True
            return
        _render_phase_rerender_count += 1
        return
    if _batched_mode is not None:
        _trace("hooks.rerender_batched", deferred=True, mode=_batched_mode)
        _batched_pending = True
        return
    if _schedule_update_callback:
        if _auto_batch_timer is None:
            scheduled_callback = _schedule_update_callback

            def _flush():
                _trace(
                    "hooks.auto_batch_flush",
                    reason="callback",
                    fiber=_current_component_id,
                    priority=resolved_priority,
                )
                if callable(scheduled_callback):
                    scheduled_callback(
                        _current_component_id,
                        _consume_pending_rerender_priority() or _coerce_priority(priority),
                    )
                _clear_auto_batch()

            _auto_batch_timer = threading.Timer(
                0,
                _flush,
            )
            _auto_batch_timer.start()
        return
    if _auto_batch_timer is None:
        rerender_callback = _rerender_callback

        def _flush() -> None:
            _trace(
                "hooks.rerender_direct_flush",
                priority=resolved_priority,
                component=_current_component_id,
            )
            ((rerender_callback() if callable(rerender_callback) else None), _clear_auto_batch())

        _auto_batch_timer = threading.Timer(
            0,
            _flush,
        )
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
    _trace("hooks.batch_enter", priority=priority, fiber=_current_component_id)
    try:
        yield
    finally:
        _batched_mode = previous
        _trace("hooks.batch_exit", priority=priority, pending=_batched_pending, next_mode=previous)
        if _batched_pending:
            _pending_rerender_priority = _merge_priority(_pending_rerender_priority, _coerce_priority(priority))
            if _schedule_update_callback:
                callback = _schedule_update_callback
                _trace("hooks.batch_flush", mode=priority)
                (
                    callback(
                        _current_component_id,
                        _consume_pending_rerender_priority() or _coerce_priority(priority),
                    )
                    if callable(callback)
                    else None
                )
            elif _rerender_callback:
                _rerender_callback()
        _batched_pending = False


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
        global _render_phase_rerender_count
        previous = state.hooks[index]
        value = next_value(previous) if callable(next_value) else next_value
        state.hooks[index] = value
        if component_id is not None:
            _dirty_components.add(component_id)
            _trace(
                "hooks.state_set",
                component_id=component_id,
                index=index,
                has_functional=callable(next_value),
                old_type=type(previous).__name__,
                new_type=type(state.hooks[index]).__name__,
            )
        if _running_effect_kind in {"layout", "insertion"}:
            _render_phase_rerender_count += 1
            return
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


def useDeferredValue(value, initial_value=None):
    """
    React useDeferredValue 实现

    延迟返回值的更新，优先渲染其他内容。
    用于延迟更新非关键的 UI 部分，让关键更新先完成。

    Args:
        value: 当前值
        initial_value: 可选的初始值（用于 SSR  hydration）

    Returns:
        延迟后的值

    使用场景:
        - 大型列表渲染时，延迟过滤条件的更新
        - 文本搜索时，延迟搜索结果的更新
        - 图片处理时，延迟处理参数的更新

    示例:
        def SearchResults(query):
            deferred_query = useDeferredValue(query)
            # 使用 deferred_query 进行搜索，而不是直接使用 query
            return <List items={search(deferred_query)} />
    """
    from .use_app import useApp

    # 如果未提供初始值，使用当前值
    if initial_value is None:
        initial_value = value

    # 获取当前组件状态
    slot, index, state = _get_slot(lambda: {"value": initial_value, "prev_value": None})

    # 检查值是否变化
    if slot["prev_value"] != value:
        slot["prev_value"] = value

        # 检查是否是首次渲染
        if slot["value"] == initial_value and initial_value == value:
            # 首次渲染，直接返回
            slot["value"] = value
        else:
            # 值变化了，检查是否需要延迟
            app = useApp()

            # 如果不是并发模式，直接更新
            if app is None or not getattr(getattr(app, "options", None), "concurrent", False):
                slot["value"] = value
            else:
                # 并发模式：延迟更新
                # 先保持旧值，调度一个过渡更新
                _schedule_rerender("transition")

                def update_deferred():
                    slot["value"] = value
                    # 触发重新渲染
                    if _rerender_callback:
                        _rerender_callback()

                # 使用过渡优先级调度更新
                app._schedule_transition(update_deferred, delay=0.08)

    return slot["value"]


def useContext(context):
    if _current_component_id is not None:
        state = _hook_state.get(_current_component_id)
        if state is not None:
            state.context_dependent = True
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
    "useDeferredValue",
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
        "pending_passive_mount_effects": len(_runtime.pending_passive_mount_effects),
    }


def _component_can_bail_out(instance_id: str) -> bool:
    if instance_id in _dirty_components:
        return False
    state = _hook_state.get(instance_id)
    if state is None:
        return True
    if state.context_dependent:
        return False
    return all(not (isinstance(hook, _EffectRecord) and hook.deps is None) for hook in state.hooks)
    return True
