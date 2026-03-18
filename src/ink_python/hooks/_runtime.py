"""
Internal hooks runtime for ink-python.

Public compatibility imports remain in `hooks/state.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Generic, Optional, TypeVar, Union

T = TypeVar("T")
Deps = tuple[Any, ...]


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


@dataclass
class Ref(Generic[T]):
    current: Optional[T] = None


_runtime = RuntimeState()
_rerender_callback: Optional[Callable[[], None]] = None


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


def _clear_hook_state() -> None:
    for state in _runtime.instances.values():
        for effect in state.effects.values():
            _run_cleanup(effect.cleanup)
    _runtime.instances.clear()
    _runtime.instance_stack.clear()
    _runtime.visited_instances.clear()
    _runtime.pending_effects.clear()
    _runtime.render_cycle_active = False


def _set_rerender_callback(callback: Optional[Callable[[], None]]) -> None:
    global _rerender_callback
    _rerender_callback = callback


def _request_rerender() -> None:
    if _runtime.batch_depth > 0:
        _runtime.rerender_pending = True
        return

    if _rerender_callback is not None:
        _rerender_callback()


def _flush_batched_rerender() -> None:
    if not _runtime.rerender_pending:
        return
    _runtime.rerender_pending = False
    if _rerender_callback is not None:
        _rerender_callback()


def batchUpdates(callback: Callable[[], T]) -> T:
    _runtime.batch_depth += 1
    try:
        return callback()
    finally:
        _runtime.batch_depth -= 1
        if _runtime.batch_depth == 0:
            _flush_batched_rerender()


def useState(
    initial_value: Union[T, Callable[[], T]],
) -> tuple[T, Callable[[Union[T, Callable[[T], T]]], None]]:
    state = _get_current_state()
    index = state.index
    state.index += 1
    if index >= len(state.states):
        value = initial_value() if callable(initial_value) else initial_value
        state.states.append(value)
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
    if index not in state.refs:
        state.refs[index] = Ref(initial_value)
    return state.refs[index]


def useMemo(factory: Callable[[], T], deps: Deps) -> T:
    state = _get_current_state()
    index = state.index
    state.index += 1
    normalized_deps = tuple(deps)
    if index in state.memos:
        old_value, old_deps = state.memos[index]
        if not _deps_changed(old_deps, normalized_deps):
            return old_value
    new_value = factory()
    state.memos[index] = (new_value, normalized_deps)
    return new_value


def useCallback(callback: Callable, deps: Deps) -> Callable:
    return useMemo(lambda: callback, deps)


def useReducer(
    reducer: Callable[[T, Any], T],
    initial_state: T,
    init: Optional[Callable[[T], T]] = None,
) -> tuple[T, Callable[[Any], None]]:
    if init is not None:
        initial_state = init(initial_state)
    state, set_state = useState(initial_state)

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
    "batchUpdates",
    "Ref",
]
