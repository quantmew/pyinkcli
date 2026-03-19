"""
Internal hooks runtime for pyinkcli.

Public compatibility imports remain in `hooks/state.py`.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, Literal, Optional, TypeVar, Union

T = TypeVar("T")
Deps = tuple[Any, ...]
UpdatePriority = Literal["default", "discrete", "render_phase"]


@dataclass
class EffectRecord:
    deps: Optional[Deps] = None
    cleanup: Optional[Callable[[], None]] = None


@dataclass
class HookState:
    index: int = 0
    states: list[Any] = field(default_factory=list)
    effects: dict[int, EffectRecord] = field(default_factory=dict)
    refs: dict[int, Any] = field(default_factory=dict)
    memos: dict[int, tuple[Any, Deps]] = field(default_factory=dict)
    kinds: dict[int, str] = field(default_factory=dict)


@dataclass
class PendingEffect:
    instance_id: str
    hook_index: int
    effect: Callable[[], Optional[Callable[[], None]]]
    deps: Optional[Deps]


@dataclass
class RuntimeState:
    instances: dict[str, HookState] = field(default_factory=dict)
    instance_stack: list[str] = field(default_factory=list)
    visited_instances: set[str] = field(default_factory=set)
    pending_effects: list[PendingEffect] = field(default_factory=list)
    render_cycle_active: bool = False
    batch_depth: int = 0
    rerender_pending: bool = False
    current_update_priority: UpdatePriority = "default"
    pending_update_priority: Optional[UpdatePriority] = None
    after_batch_callbacks: list[Callable[[], None]] = field(default_factory=list)


@dataclass
class Ref(Generic[T]):
    current: Optional[T] = None


_runtime = RuntimeState()
_rerender_callback: Optional[Callable[[], None]] = None
_UNSET = object()


def _has_initialized_state_slot(state: HookState, hook_index: int) -> bool:
    return (
        0 <= hook_index < len(state.states)
        and state.states[hook_index] is not _UNSET
    )


def _clone_hook_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _clone_hook_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clone_hook_value(item) for item in value]
    return value


def _resolve_nested_parent(
    target: Any,
    path: list[Any],
) -> tuple[Any, Any, bool]:
    current = target
    for key in path[:-1]:
        if isinstance(key, int):
            if not isinstance(current, list) or key >= len(current):
                return (None, None, False)
            current = current[key]
            continue
        if not isinstance(current, dict) or key not in current:
            return (None, None, False)
        current = current[key]
    return (current, path[-1], True)


def _set_nested_value(target: Any, path: list[Any], value: Any) -> bool:
    if not path:
        return False
    current = target
    for key in path[:-1]:
        if isinstance(key, int):
            if not isinstance(current, list):
                return False
            while len(current) <= key:
                current.append({})
            if not isinstance(current[key], (dict, list)):
                current[key] = {}
            current = current[key]
            continue
        if not isinstance(current, dict):
            return False
        next_value = current.get(key)
        if not isinstance(next_value, (dict, list)):
            next_value = {}
            current[key] = next_value
        current = next_value
    last_key = path[-1]
    if isinstance(last_key, int):
        if not isinstance(current, list):
            return False
        while len(current) <= last_key:
            current.append(None)
        current[last_key] = _clone_hook_value(value)
        return True
    if not isinstance(current, dict):
        return False
    current[last_key] = _clone_hook_value(value)
    return True


def _delete_nested_value(target: Any, path: list[Any]) -> bool:
    if not path:
        return False
    parent, key, found = _resolve_nested_parent(target, path)
    if not found:
        return False
    if isinstance(key, int):
        if not isinstance(parent, list) or key >= len(parent):
            return False
        parent.pop(key)
        return True
    if not isinstance(parent, dict) or key not in parent:
        return False
    parent.pop(key)
    return True


def _pop_nested_value(target: Any, path: list[Any]) -> tuple[Any, bool]:
    if not path:
        return (None, False)
    parent, key, found = _resolve_nested_parent(target, path)
    if not found:
        return (None, False)
    if isinstance(key, int):
        if not isinstance(parent, list) or key >= len(parent):
            return (None, False)
        return (parent.pop(key), True)
    if not isinstance(parent, dict) or key not in parent:
        return (None, False)
    return (parent.pop(key), True)


def _normalize_deps(deps: Optional[Deps]) -> Optional[Deps]:
    if deps is None:
        return None
    return tuple(deps)


def _deps_changed(old_deps: Optional[Deps], new_deps: Optional[Deps]) -> bool:
    if old_deps is None or new_deps is None:
        return True
    if len(old_deps) != len(new_deps):
        return True
    return any(old is not new and old != new for old, new in zip(old_deps, new_deps))


def _get_current_instance_id() -> str:
    if _runtime.instance_stack:
        return _runtime.instance_stack[-1]
    return "__global__"


def _get_current_state() -> HookState:
    instance_id = _get_current_instance_id()
    state = _runtime.instances.get(instance_id)
    if state is None:
        state = HookState()
        _runtime.instances[instance_id] = state
    return state


def _reset_hook_state() -> None:
    _runtime.render_cycle_active = True
    _runtime.visited_instances.clear()
    _runtime.pending_effects.clear()


def _begin_component_render(instance_id: str) -> None:
    state = _runtime.instances.get(instance_id)
    if state is None:
        state = HookState()
        _runtime.instances[instance_id] = state
    state.index = 0
    _runtime.instance_stack.append(instance_id)
    _runtime.visited_instances.add(instance_id)


def _end_component_render() -> None:
    if _runtime.instance_stack:
        _runtime.instance_stack.pop()


def _run_cleanup(cleanup: Optional[Callable[[], None]]) -> None:
    if cleanup is None:
        return
    try:
        cleanup()
    except Exception:
        pass


def _flush_pending_effects() -> None:
    for pending in _runtime.pending_effects:
        state = _runtime.instances.get(pending.instance_id)
        if state is None:
            continue
        previous = state.effects.get(pending.hook_index)
        if previous is not None:
            _run_cleanup(previous.cleanup)
        cleanup = pending.effect()
        state.effects[pending.hook_index] = EffectRecord(
            deps=pending.deps,
            cleanup=cleanup,
        )
    _runtime.pending_effects.clear()


def _cleanup_unmounted_instances() -> None:
    removed_ids = [
        instance_id
        for instance_id in _runtime.instances
        if instance_id != "__global__" and instance_id not in _runtime.visited_instances
    ]
    for instance_id in removed_ids:
        state = _runtime.instances.pop(instance_id, None)
        if state is None:
            continue
        for effect in state.effects.values():
            _run_cleanup(effect.cleanup)


def _finish_hook_state() -> None:
    if not _runtime.render_cycle_active:
        return
    _flush_pending_effects()
    _cleanup_unmounted_instances()
    _runtime.render_cycle_active = False
    if _runtime.batch_depth == 0:
        _run_after_batch_callbacks()


def _clear_hook_state() -> None:
    for state in _runtime.instances.values():
        for effect in state.effects.values():
            _run_cleanup(effect.cleanup)
    _runtime.instances.clear()
    _runtime.instance_stack.clear()
    _runtime.visited_instances.clear()
    _runtime.pending_effects.clear()
    _runtime.render_cycle_active = False
    _runtime.batch_depth = 0
    _runtime.rerender_pending = False
    _runtime.current_update_priority = "default"
    _runtime.pending_update_priority = None
    _runtime.after_batch_callbacks.clear()


def _set_rerender_callback(callback: Optional[Callable[[], None]]) -> None:
    global _rerender_callback
    _rerender_callback = callback


def _priority_rank(priority: UpdatePriority) -> int:
    if priority == "render_phase":
        return 2
    if priority == "discrete":
        return 1
    return 0


def _queue_pending_rerender(priority: UpdatePriority) -> None:
    _runtime.rerender_pending = True
    current = _runtime.pending_update_priority
    if current is None or _priority_rank(priority) > _priority_rank(current):
        _runtime.pending_update_priority = priority


def _consume_pending_rerender_priority() -> Optional[UpdatePriority]:
    if not _runtime.rerender_pending:
        return None
    _runtime.rerender_pending = False
    priority = _runtime.pending_update_priority or "default"
    _runtime.pending_update_priority = None
    return priority


def _has_pending_rerender() -> bool:
    return _runtime.rerender_pending


def _has_rerender_target() -> bool:
    return _rerender_callback is not None or _runtime.render_cycle_active or _runtime.batch_depth > 0


def _override_hook_state(
    instance_id: str,
    path: list[Any],
    value: Any,
) -> bool:
    if not path:
        return False
    state = _runtime.instances.get(instance_id)
    if state is None:
        return False
    hook_index = path[0]
    if not isinstance(hook_index, int) or not _has_initialized_state_slot(state, hook_index):
        return False
    if len(path) == 1:
        state.states[hook_index] = _clone_hook_value(value)
        return True
    target = state.states[hook_index]
    return _set_nested_value(target, path[1:], value)


def _get_hook_state_snapshot(instance_id: str) -> Optional[list[dict[str, Any]]]:
    state = _runtime.instances.get(instance_id)
    if state is None:
        return None

    hook_indexes = set(state.kinds.keys())
    hook_indexes.update(range(len(state.states)))
    hook_indexes.update(state.effects.keys())
    hook_indexes.update(state.refs.keys())
    hook_indexes.update(state.memos.keys())

    snapshot: list[dict[str, Any]] = []
    for hook_index in sorted(hook_indexes):
        kind = state.kinds.get(hook_index, "Unknown")
        value: Any = None
        if _has_initialized_state_slot(state, hook_index):
            value = _clone_hook_value(state.states[hook_index])
        elif hook_index in state.refs:
            ref = state.refs[hook_index]
            value = {"current": _clone_hook_value(getattr(ref, "current", None))}
        elif hook_index in state.memos:
            value = _clone_hook_value(state.memos[hook_index][0])

        snapshot.append(
            {
                "id": hook_index,
                "name": kind,
                "value": value,
                "isStateEditable": kind in ("State", "Reducer"),
            }
        )

    return snapshot


def _delete_hook_state_path(
    instance_id: str,
    path: list[Any],
) -> bool:
    if len(path) < 2:
        return False
    state = _runtime.instances.get(instance_id)
    if state is None:
        return False
    hook_index = path[0]
    if not isinstance(hook_index, int) or not _has_initialized_state_slot(state, hook_index):
        return False
    return _delete_nested_value(state.states[hook_index], path[1:])


def _rename_hook_state_path(
    instance_id: str,
    old_path: list[Any],
    new_path: list[Any],
) -> bool:
    if not old_path or not new_path:
        return False
    if old_path[0] != new_path[0]:
        return False
    if len(old_path) < 2 or len(new_path) < 2:
        return False
    state = _runtime.instances.get(instance_id)
    if state is None:
        return False
    hook_index = old_path[0]
    if not isinstance(hook_index, int) or not _has_initialized_state_slot(state, hook_index):
        return False
    target = state.states[hook_index]
    value, found = _pop_nested_value(target, old_path[1:])
    if not found:
        return False
    return _set_nested_value(target, new_path[1:], value)


def _request_rerender() -> None:
    priority: UpdatePriority = (
        "render_phase" if _runtime.render_cycle_active else _runtime.current_update_priority
    )

    _queue_pending_rerender(priority)

    if _runtime.render_cycle_active:
        if _runtime.batch_depth == 0 and _rerender_callback is not None:
            _runtime.after_batch_callbacks.append(_rerender_callback)
        return

    if _runtime.batch_depth > 0:
        return

    if _rerender_callback is not None:
        _rerender_callback()


def _flush_batched_rerender() -> None:
    if not _has_pending_rerender():
        return
    if _runtime.render_cycle_active:
        if _rerender_callback is not None:
            _runtime.after_batch_callbacks.append(_rerender_callback)
        return
    if _rerender_callback is not None:
        _rerender_callback()


def _run_after_batch_callbacks() -> None:
    callbacks = _runtime.after_batch_callbacks[:]
    _runtime.after_batch_callbacks.clear()
    for callback in callbacks:
        try:
            callback()
        except Exception:
            pass


def _queue_after_current_batch(callback: Callable[[], None]) -> None:
    if _runtime.render_cycle_active or _runtime.batch_depth > 0:
        _runtime.after_batch_callbacks.append(callback)
        return

    callback()


def _batched_updates_runtime(callback: Callable[[], T]) -> T:
    _runtime.batch_depth += 1
    try:
        return callback()
    finally:
        _runtime.batch_depth -= 1
        if _runtime.batch_depth == 0:
            _flush_batched_rerender()
            _run_after_batch_callbacks()


def _discrete_updates_runtime(callback: Callable[[], T]) -> T:
    previous = _runtime.current_update_priority
    _runtime.current_update_priority = "discrete"
    try:
        return _batched_updates_runtime(callback)
    finally:
        _runtime.current_update_priority = previous


def useState(
    initial_value: Union[T, Callable[[], T]],
) -> tuple[T, Callable[[Union[T, Callable[[T], T]]], None]]:
    state = _get_current_state()
    index = state.index
    state.index += 1
    state.kinds[index] = "State"
    if index >= len(state.states):
        state.states.extend([_UNSET] * (index + 1 - len(state.states)))

    if state.states[index] is _UNSET:
        value = initial_value() if callable(initial_value) else initial_value
        state.states[index] = value
    current_value = state.states[index]

    def set_value(new_value: Union[T, Callable[[T], T]]) -> None:
        if callable(new_value):
            state.states[index] = new_value(state.states[index])
        else:
            state.states[index] = new_value
        _request_rerender()

    return (current_value, set_value)


def useEffect(
    effect: Callable[[], Optional[Callable[[], None]]],
    deps: Optional[Deps] = None,
) -> None:
    state = _get_current_state()
    index = state.index
    state.index += 1
    state.kinds[index] = "Effect"
    normalized_deps = _normalize_deps(deps)
    previous = state.effects.get(index)
    if previous is not None and not _deps_changed(previous.deps, normalized_deps):
        return
    if _runtime.render_cycle_active and _runtime.instance_stack:
        _runtime.pending_effects.append(
            PendingEffect(
                instance_id=_get_current_instance_id(),
                hook_index=index,
                effect=effect,
                deps=normalized_deps,
            )
        )
        return
    _run_cleanup(previous.cleanup if previous else None)
    cleanup = effect()
    state.effects[index] = EffectRecord(deps=normalized_deps, cleanup=cleanup)


def useRef(initial_value: Optional[T] = None) -> Ref[T]:
    state = _get_current_state()
    index = state.index
    state.index += 1
    state.kinds[index] = "Ref"
    if index not in state.refs:
        state.refs[index] = Ref(initial_value)
    return state.refs[index]


def useMemo(factory: Callable[[], T], deps: Deps) -> T:
    state = _get_current_state()
    index = state.index
    state.index += 1
    state.kinds[index] = "Memo"
    normalized_deps = tuple(deps)
    if index in state.memos:
        old_value, old_deps = state.memos[index]
        if not _deps_changed(old_deps, normalized_deps):
            return old_value
    new_value = factory()
    state.memos[index] = (new_value, normalized_deps)
    return new_value


def useCallback(callback: Callable, deps: Deps) -> Callable:
    state = _get_current_state()
    index = state.index
    value = useMemo(lambda: callback, deps)
    state.kinds[index] = "Callback"
    return value


def useReducer(
    reducer: Callable[[T, Any], T],
    initial_state: T,
    init: Optional[Callable[[T], T]] = None,
) -> tuple[T, Callable[[Any], None]]:
    if init is not None:
        initial_state = init(initial_state)
    index = _get_current_state().index
    state, set_state = useState(initial_state)
    _get_current_state().kinds[index] = "Reducer"

    def dispatch(action: Any) -> None:
        set_state(lambda current: reducer(current, action))

    return (state, dispatch)


__all__ = [
    "useState",
    "useEffect",
    "useRef",
    "useMemo",
    "useCallback",
    "useReducer",
    "Ref",
    "_get_hook_state_snapshot",
    "_override_hook_state",
    "_delete_hook_state_path",
    "_rename_hook_state_path",
]
