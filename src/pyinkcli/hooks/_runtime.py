"""
Internal hooks runtime for pyinkcli.

Public compatibility imports remain in `hooks/state.py`.
"""

from __future__ import annotations

import math
import threading
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from pyinkcli.components._app_context_runtime import _get_app_context
from pyinkcli.packages.react_reconciler.ReactFiberFlags import NoFlags, Passive
from pyinkcli.packages.react_reconciler.ReactEventPriorities import (
    DefaultEventPriority,
    DiscreteEventPriority,
    EventPriority,
    NoEventPriority,
    RenderPhaseUpdatePriority,
    TransitionEventPriority,
    higherEventPriority,
)
from pyinkcli.packages.react_reconciler.ReactSharedInternals import shared_internals

T = TypeVar("T")
Deps = tuple[Any, ...]
UpdatePriority = EventPriority
BasicStateAction = Any
_UNSET = object()
HookHasEffect = 1 << 0
HookPassive = 1 << 1
HookLayout = 1 << 2
HookInsertion = 1 << 3


@dataclass
class EffectInstance:
    destroy: Callable[[], None] | None = None


@dataclass
class EffectRecord:
    tag: int
    create: Callable[[], Callable[[], None] | None]
    deps: Deps | None
    inst: EffectInstance
    instance_id: str | None = None
    hook_index: int | None = None
    next: EffectRecord | None = None


@dataclass
class FunctionComponentUpdateQueue:
    last_effect: EffectRecord | None = None

@dataclass
class Update(Generic[T]):
    action: Any
    priority: UpdatePriority = NoEventPriority
    has_eager_state: bool = False
    eager_state: T | None = None


@dataclass
class UpdateQueue(Generic[T]):
    pending: list[Update[T]] = field(default_factory=list)
    dispatch: Callable[[Any], None] | None = None
    last_rendered_reducer: Callable[[T, Any], T] | None = None
    last_rendered_state: T | None = None


@dataclass
class HookNode:
    index: int
    kind: str = "Unknown"
    memoized_state: Any = _UNSET
    base_state: Any = _UNSET
    base_queue: list[Update[Any]] = field(default_factory=list)
    queue: UpdateQueue[Any] | None = None
    deps: Deps | None = None
    cleanup: Callable[[], None] | None = None
    ref: Any = None
    memoized_value: Any = _UNSET
    memoized_deps: Deps | None = None
    next: HookNode | None = None


@dataclass
class HookFiber:
    component_id: str
    element_type: str
    tag: int = 0
    key: str | None = None
    path: tuple[Any, ...] = ()
    pending_props: dict[str, Any] | None = None
    memoized_props: dict[str, Any] | None = None
    return_fiber: HookFiber | None = None
    child: HookFiber | None = None
    sibling: HookFiber | None = None
    state_node: Any = None
    flags: int = NoFlags
    subtree_flags: int = NoFlags
    deletions: list[HookFiber] = field(default_factory=list)
    ref_detachments: list[Any] = field(default_factory=list)
    layout_callbacks: list[Callable[[], None]] = field(default_factory=list)
    passive_callbacks: list[Callable[[], None]] = field(default_factory=list)
    update_queue: FunctionComponentUpdateQueue | None = None
    index: int = 0
    hook_head: HookNode | None = None
    hook_tail: HookNode | None = None
    current_hook: HookNode | None = None
    alternate: HookFiber | None = None
    is_work_in_progress: bool = False


@dataclass
class PendingEffect:
    instance_id: str
    hook_index: int
    hook_flags: int
    effect: Callable[[], Callable[[], None] | None]
    deps: Deps | None


@dataclass
class RuntimeState:
    fibers: dict[str, HookFiber] = field(default_factory=dict)
    fiber_stack: list[HookFiber] = field(default_factory=list)
    visited_instances: set[str] = field(default_factory=set)
    pending_effects: list[PendingEffect] = field(default_factory=list)
    pending_passive_unmount_fibers: list[HookFiber] = field(default_factory=list)
    render_cycle_active: bool = False
    batch_depth: int = 0
    rerender_pending: bool = False
    pending_update_lanes: int = NoEventPriority
    pending_update_priority: UpdatePriority = NoEventPriority
    pending_update_source: str | None = None
    pending_fiber: HookFiber | None = None
    after_batch_callbacks: list[Callable[[], None]] = field(default_factory=list)


@dataclass
class Ref(Generic[T]):
    current: T | None = None


_runtime = RuntimeState()
_schedule_update_callback: Callable[[HookFiber | None, UpdatePriority], None] | None = None
_compat_rerender_callback: Callable[[], None] | None = None
_compat_rerender_scheduled = False
_scheduled_update_flush = False
_defer_passive_effects_to_commit = False
_defer_non_passive_hook_effects_to_commit = False


def _flush_scheduled_rerender() -> bool:
    global _scheduled_update_flush
    _scheduled_update_flush = False
    callback = _schedule_update_callback
    if callback is None:
        return False
    priority = _consume_pending_rerender_priority_numeric()
    fiber = _runtime.pending_fiber
    _runtime.pending_fiber = None
    if priority is None:
        return False
    callback(fiber, priority)
    return True


def _schedule_update_flush() -> None:
    global _scheduled_update_flush
    if _scheduled_update_flush:
        return
    _scheduled_update_flush = True

    def run_callback() -> None:
        _flush_scheduled_rerender()

    if _runtime.render_cycle_active or _runtime.batch_depth > 0:
        _runtime.after_batch_callbacks.append(run_callback)
        return

    threading.Timer(0.001, run_callback).start()


def _get_hook_node_by_index(fiber: HookFiber, hook_index: int) -> HookNode | None:
    current = fiber.hook_head
    while current is not None:
        if current.index == hook_index:
            return current
        current = current.next
    return None


def _has_initialized_state_slot(fiber: HookFiber, hook_index: int) -> bool:
    node = _get_hook_node_by_index(fiber, hook_index)
    return node is not None and node.memoized_state is not _UNSET


def _clone_hook_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _clone_hook_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clone_hook_value(item) for item in value]
    return value


def _state_values_equal(previous: Any, next_value: Any) -> bool:
    if previous is next_value:
        return True

    if isinstance(previous, float) and isinstance(next_value, float):
        if math.isnan(previous) and math.isnan(next_value):
            return True
        return previous == next_value

    immutable_types = (str, bytes, int, bool, tuple, frozenset, type(None))
    if isinstance(previous, immutable_types) and isinstance(next_value, immutable_types):
        return previous == next_value

    return False


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


def _normalize_deps(deps: Deps | None) -> Deps | None:
    if deps is None:
        return None
    return tuple(deps)


def _deps_changed(old_deps: Deps | None, new_deps: Deps | None) -> bool:
    if old_deps is None or new_deps is None:
        return True
    if len(old_deps) != len(new_deps):
        return True
    return any(
        old is not new and old != new
        for old, new in zip(old_deps, new_deps)
    )


def _get_current_instance_id() -> str:
    if _runtime.fiber_stack:
        return _runtime.fiber_stack[-1].component_id
    return "__global__"


def _get_or_create_fiber(
    component_id: str,
    *,
    tag: int = 0,
    element_type: str = "function",
    key: str | None = None,
    path: tuple[Any, ...] = (),
    pending_props: dict[str, Any] | None = None,
    memoized_props: dict[str, Any] | None = None,
    return_fiber: HookFiber | None = None,
) -> HookFiber:
    fiber = _runtime.fibers.get(component_id)
    if fiber is None:
        fiber = HookFiber(
            component_id=component_id,
            tag=tag,
            element_type=element_type,
            key=key,
            path=path,
            pending_props=pending_props,
            memoized_props=memoized_props,
            return_fiber=return_fiber,
        )
        _runtime.fibers[component_id] = fiber
    else:
        fiber.tag = tag
        fiber.element_type = element_type
        fiber.key = key
        fiber.path = path
        fiber.pending_props = pending_props
        fiber.memoized_props = memoized_props if memoized_props is not None else fiber.memoized_props
        fiber.return_fiber = return_fiber
    return fiber


def _get_current_fiber() -> HookFiber:
    if _runtime.fiber_stack:
        return _runtime.fiber_stack[-1]
    component_id = _get_current_instance_id()
    return _get_or_create_fiber(component_id)


def _clone_hook_chain(head: HookNode | None) -> tuple[HookNode | None, HookNode | None]:
    if head is None:
        return (None, None)

    cloned_head: HookNode | None = None
    cloned_tail: HookNode | None = None
    current = head
    while current is not None:
        cloned = HookNode(
            index=current.index,
            kind=current.kind,
            memoized_state=current.memoized_state,
            base_state=current.base_state,
            base_queue=list(current.base_queue),
            queue=current.queue,
            deps=current.deps,
            cleanup=current.cleanup,
            ref=current.ref,
            memoized_value=current.memoized_value,
            memoized_deps=current.memoized_deps,
        )
        if cloned_head is None:
            cloned_head = cloned
            cloned_tail = cloned
        else:
            assert cloned_tail is not None
            cloned_tail.next = cloned
            cloned_tail = cloned
        current = current.next
    return (cloned_head, cloned_tail)


def _create_work_in_progress_fiber(current: HookFiber) -> HookFiber:
    work_in_progress = current.alternate
    if work_in_progress is None:
        work_in_progress = HookFiber(
            component_id=current.component_id,
            tag=current.tag,
            element_type=current.element_type,
            key=current.key,
            path=current.path,
            pending_props=current.pending_props,
            memoized_props=current.memoized_props,
            return_fiber=current.return_fiber,
            child=None,
            sibling=None,
            state_node=current.state_node,
            flags=NoFlags,
            subtree_flags=NoFlags,
            deletions=[],
            ref_detachments=[],
            layout_callbacks=[],
            passive_callbacks=[],
            update_queue=current.update_queue,
            is_work_in_progress=True,
        )
        work_in_progress.alternate = current
        current.alternate = work_in_progress
    work_in_progress.tag = current.tag
    work_in_progress.element_type = current.element_type
    work_in_progress.key = current.key
    work_in_progress.path = current.path
    work_in_progress.pending_props = current.pending_props
    work_in_progress.memoized_props = current.memoized_props
    work_in_progress.return_fiber = current.return_fiber
    work_in_progress.child = None
    work_in_progress.sibling = None
    work_in_progress.state_node = current.state_node
    work_in_progress.flags = NoFlags
    work_in_progress.subtree_flags = NoFlags
    work_in_progress.deletions = []
    work_in_progress.ref_detachments = []
    work_in_progress.layout_callbacks = []
    work_in_progress.passive_callbacks = []
    work_in_progress.update_queue = current.update_queue
    work_in_progress.index = 0
    work_in_progress.is_work_in_progress = True
    (
        work_in_progress.hook_head,
        work_in_progress.hook_tail,
    ) = _clone_hook_chain(current.hook_head)
    work_in_progress.current_hook = work_in_progress.hook_head
    return work_in_progress


def _commit_completed_fiber(
    work_in_progress: HookFiber,
    registry: dict[str, HookFiber] | None = None,
) -> HookFiber:
    current = work_in_progress.alternate
    if current is not None:
        current.alternate = work_in_progress
    work_in_progress.memoized_props = work_in_progress.pending_props
    work_in_progress.current_hook = None
    work_in_progress.is_work_in_progress = False
    subtree_flags = NoFlags
    child = work_in_progress.child
    while child is not None:
        subtree_flags |= child.flags | child.subtree_flags
        child = child.sibling
    work_in_progress.subtree_flags = subtree_flags
    if registry is not None:
        registry[work_in_progress.component_id] = work_in_progress
    return work_in_progress


def _append_hook_node(fiber: HookFiber, node: HookNode) -> HookNode:
    if fiber.hook_head is None:
        fiber.hook_head = node
        fiber.hook_tail = node
    else:
        assert fiber.hook_tail is not None
        fiber.hook_tail.next = node
        fiber.hook_tail = node
    return node


def _advance_current_hook(fiber: HookFiber) -> HookNode | None:
    current = fiber.current_hook
    if current is not None:
        fiber.current_hook = current.next
    return current


def _get_or_create_hook(fiber: HookFiber, kind: str) -> HookNode:
    index = fiber.index
    fiber.index += 1
    existing = _advance_current_hook(fiber)
    if existing is not None:
        existing.kind = kind
        return existing
    return _append_hook_node(fiber, HookNode(index=index, kind=kind))


def _basic_state_reducer(state: T, action: BasicStateAction) -> T:
    return action(state) if callable(action) else action


def _enqueue_hook_update(queue: UpdateQueue[T], update: Update[T]) -> None:
    queue.pending.append(update)


def _get_current_update_priority() -> UpdatePriority:
    if _runtime.render_cycle_active:
        return RenderPhaseUpdatePriority
    if shared_internals.current_transition is not None:
        return TransitionEventPriority
    if shared_internals.current_update_priority != NoEventPriority:
        return shared_internals.current_update_priority
    return DefaultEventPriority


def _get_current_update_source() -> str:
    if _runtime.render_cycle_active:
        return "render_phase"
    if shared_internals.current_transition is not None:
        return "transition"
    if shared_internals.current_update_priority == DiscreteEventPriority:
        return "discrete"
    return "default"


def _should_process_update(
    update_priority: UpdatePriority,
    render_priority: UpdatePriority,
) -> bool:
    if render_priority == NoEventPriority:
        return True
    return update_priority <= render_priority


def _process_hook_queue(
    hook: HookNode,
    reducer: Callable[[T, Any], T],
    initial_value: T,
    fiber: HookFiber | None = None,
) -> tuple[T, UpdateQueue[T]]:
    queue = hook.queue
    if queue is None:
        queue = UpdateQueue[T]()
        hook.queue = queue

    current_value: T
    if hook.memoized_state is _UNSET:
        hook.memoized_state = initial_value
        hook.base_state = initial_value
        current_value = initial_value
    else:
        current_value = hook.memoized_state

    if queue.pending:
        hook.base_queue.extend(queue.pending)
        queue.pending.clear()

    if hook.base_queue:
        next_value = hook.base_state if hook.base_state is not _UNSET else current_value
        new_base_state = next_value
        new_base_queue: list[Update[T]] = []
        did_skip_update = False
        highest_remaining_priority = NoEventPriority
        render_priority = shared_internals.current_render_priority or DefaultEventPriority

        for update in hook.base_queue:
            if not _should_process_update(update.priority, render_priority):
                if not did_skip_update:
                    new_base_state = next_value
                    did_skip_update = True
                new_base_queue.append(update)
                highest_remaining_priority = higherEventPriority(
                    highest_remaining_priority,
                    update.priority,
                )
                continue

            next_value = reducer(next_value, update.action)

            if did_skip_update:
                new_base_queue.append(
                    Update(
                        action=update.action,
                        priority=NoEventPriority,
                    )
                )

        hook.memoized_state = next_value
        hook.base_state = new_base_state if did_skip_update else next_value
        hook.base_queue = new_base_queue
        current_value = next_value
        if highest_remaining_priority != NoEventPriority:
            _queue_pending_rerender(
                highest_remaining_priority,
                fiber=fiber,
                source="transition" if highest_remaining_priority == TransitionEventPriority else "default",
            )

    queue.last_rendered_reducer = reducer
    queue.last_rendered_state = current_value
    return current_value, queue


def _create_hook_dispatch(
    hook: HookNode,
    queue: UpdateQueue[T],
    fiber: HookFiber | None,
) -> Callable[[Any], None]:
    def dispatch(action: Any) -> None:
        previous_value = (
            queue.last_rendered_state
            if queue.last_rendered_reducer is not None
            else hook.memoized_state
        )
        update = Update[T](
            action=action,
            priority=_get_current_update_priority(),
        )

        if not queue.pending and queue.last_rendered_reducer is not None:
            try:
                eager_state = queue.last_rendered_reducer(previous_value, action)
                update.has_eager_state = True
                update.eager_state = eager_state
                if _state_values_equal(previous_value, eager_state):
                    _enqueue_hook_update(queue, update)
                    return
            except Exception:
                pass

        _enqueue_hook_update(queue, update)
        _request_rerender(fiber)

    return dispatch


def _reset_hook_state() -> None:
    _runtime.render_cycle_active = True
    _runtime.visited_instances.clear()
    _runtime.pending_effects.clear()


def _begin_component_render(fiber_or_instance_id: HookFiber | str) -> HookFiber:
    if isinstance(fiber_or_instance_id, HookFiber):
        existing = _runtime.fibers.get(fiber_or_instance_id.component_id)
        if existing is None:
            fiber = fiber_or_instance_id
            _runtime.fibers[fiber.component_id] = fiber
        else:
            fiber = _get_or_create_fiber(
                fiber_or_instance_id.component_id,
                element_type=fiber_or_instance_id.element_type,
                key=fiber_or_instance_id.key,
                path=fiber_or_instance_id.path,
            )
    else:
        fiber = _get_or_create_fiber(fiber_or_instance_id)
    work_in_progress = _create_work_in_progress_fiber(fiber)
    _runtime.fiber_stack.append(work_in_progress)
    _runtime.visited_instances.add(work_in_progress.component_id)
    return work_in_progress


def _set_current_hook_fiber(fiber: HookFiber | None) -> None:
    if not _runtime.fiber_stack:
        return
    current = _runtime.fiber_stack[-1]
    if fiber is None:
        return
    current.element_type = fiber.element_type
    current.key = fiber.key
    current.path = fiber.path


def _end_component_render() -> HookFiber | None:
    if not _runtime.fiber_stack:
        return None
    work_in_progress = _runtime.fiber_stack.pop()
    return _commit_completed_fiber(work_in_progress, registry=_runtime.fibers)


def _run_cleanup(cleanup: Callable[[], None] | None) -> None:
    if cleanup is None:
        return
    with suppress(Exception):
        cleanup()


def _flush_pending_effects() -> None:
    for pending in _runtime.pending_effects:
        fiber = _runtime.fibers.get(pending.instance_id)
        if fiber is None:
            continue
        previous = _get_hook_node_by_index(fiber, pending.hook_index)
        previous_cleanup = previous.cleanup if previous is not None else None
        cleanup = None
        should_defer = (
            _defer_passive_effects_to_commit
            if pending.hook_flags & HookPassive
            else _defer_non_passive_hook_effects_to_commit
        )
        effect_tag = pending.hook_flags | HookHasEffect
        if not should_defer:
            if previous_cleanup is not None:
                _run_cleanup(previous_cleanup)
            cleanup = pending.effect()
            effect_tag = pending.hook_flags
        hook = previous or _append_hook_node(
            fiber,
            HookNode(index=pending.hook_index, kind="Effect"),
        )
        if fiber.update_queue is None:
            fiber.update_queue = FunctionComponentUpdateQueue()
        effect_record = EffectRecord(
            tag=effect_tag,
            create=pending.effect,
            deps=pending.deps,
            inst=EffectInstance(destroy=previous_cleanup),
            instance_id=pending.instance_id,
            hook_index=pending.hook_index,
        )
        last_effect = fiber.update_queue.last_effect
        if last_effect is None:
            effect_record.next = effect_record
            fiber.update_queue.last_effect = effect_record
        else:
            first_effect = last_effect.next
            last_effect.next = effect_record
            effect_record.next = first_effect
            fiber.update_queue.last_effect = effect_record
        hook.deps = pending.deps
        hook.cleanup = cleanup
    _runtime.pending_effects.clear()


def _set_defer_passive_effects_to_commit(enabled: bool) -> None:
    global _defer_passive_effects_to_commit
    _defer_passive_effects_to_commit = enabled


def _set_defer_non_passive_hook_effects_to_commit(enabled: bool) -> None:
    global _defer_non_passive_hook_effects_to_commit
    _defer_non_passive_hook_effects_to_commit = enabled


def _commit_hook_effect_list_mount(flags: int, fiber: HookFiber) -> None:
    update_queue = fiber.update_queue
    last_effect = update_queue.last_effect if update_queue is not None else None
    if last_effect is None:
        return

    current = last_effect.next
    while current is not None:
        if (current.tag & flags) == flags:
            if current.inst.destroy is not None:
                _run_cleanup(current.inst.destroy)
            cleanup = current.create()
            current.inst.destroy = cleanup
            current.tag &= ~HookHasEffect
            if current.hook_index is not None:
                hook = _get_hook_node_by_index(fiber, current.hook_index)
                if hook is not None:
                    hook.cleanup = cleanup
                    hook.deps = current.deps
        if current is last_effect:
            break
        current = current.next


def _commit_hook_passive_mount_effects(fiber: HookFiber) -> None:
    _commit_hook_effect_list_mount(HookPassive | HookHasEffect, fiber)


def _commit_hook_effect_list_unmount(flags: int, fiber: HookFiber) -> bool:
    update_queue = fiber.update_queue
    last_effect = update_queue.last_effect if update_queue is not None else None
    if last_effect is None:
        return False

    current = last_effect.next
    while current is not None:
        if (current.tag & flags) == flags:
            destroy = current.inst.destroy
            hook = (
                _get_hook_node_by_index(fiber, current.hook_index)
                if current.hook_index is not None
                else None
            )
            if destroy is None and hook is not None:
                destroy = hook.cleanup
            if destroy is not None:
                _run_cleanup(destroy)
            current.inst.destroy = None
            if hook is not None:
                hook.cleanup = None
        if current is last_effect:
            break
        current = current.next
    return True


def _commit_hook_passive_unmount_effects(fiber: HookFiber) -> None:
    if _commit_hook_effect_list_unmount(HookPassive | HookHasEffect, fiber):
        return

    current_hook = fiber.hook_head
    while current_hook is not None:
        if current_hook.cleanup is not None:
            _run_cleanup(current_hook.cleanup)
            current_hook.cleanup = None
        current_hook = current_hook.next


def _drain_pending_passive_unmount_fibers() -> list[HookFiber]:
    pending = _runtime.pending_passive_unmount_fibers[:]
    _runtime.pending_passive_unmount_fibers.clear()
    return pending


def _peek_pending_passive_unmount_fibers() -> list[HookFiber]:
    return _runtime.pending_passive_unmount_fibers[:]


def _cleanup_unmounted_instances() -> None:
    removed_ids = [
        instance_id
        for instance_id in _runtime.fibers
        if instance_id != "__global__" and instance_id not in _runtime.visited_instances
    ]
    for instance_id in removed_ids:
        fiber = _runtime.fibers.pop(instance_id, None)
        if fiber is None:
            continue
        if (
            _defer_passive_effects_to_commit
            or _defer_non_passive_hook_effects_to_commit
        ):
            _runtime.pending_passive_unmount_fibers.append(fiber)
            continue
        current = fiber.hook_head
        while current is not None:
            _run_cleanup(current.cleanup)
            current = current.next


def _finish_hook_state(
    *,
    defer_passive_effects_to_commit: bool = False,
    defer_non_passive_hook_effects_to_commit: bool = False,
) -> None:
    if not _runtime.render_cycle_active:
        return
    previous_defer = _defer_passive_effects_to_commit
    previous_non_passive_defer = _defer_non_passive_hook_effects_to_commit
    _set_defer_passive_effects_to_commit(defer_passive_effects_to_commit)
    _set_defer_non_passive_hook_effects_to_commit(
        defer_non_passive_hook_effects_to_commit
    )
    try:
        _flush_pending_effects()
        _cleanup_unmounted_instances()
        _runtime.render_cycle_active = False
        if _runtime.batch_depth == 0:
            _run_after_batch_callbacks()
    finally:
        _set_defer_passive_effects_to_commit(previous_defer)
        _set_defer_non_passive_hook_effects_to_commit(previous_non_passive_defer)


def _clear_hook_state() -> None:
    for fiber in _runtime.fibers.values():
        current = fiber.hook_head
        while current is not None:
            _run_cleanup(current.cleanup)
            current = current.next
    _runtime.fibers.clear()
    _runtime.fiber_stack.clear()
    _runtime.visited_instances.clear()
    _runtime.pending_effects.clear()
    _runtime.pending_passive_unmount_fibers.clear()
    _runtime.render_cycle_active = False
    _runtime.batch_depth = 0
    _runtime.rerender_pending = False
    _runtime.pending_update_lanes = NoEventPriority
    _runtime.pending_update_priority = NoEventPriority
    _runtime.pending_update_source = None
    _runtime.pending_fiber = None
    _runtime.after_batch_callbacks.clear()


def _set_schedule_update_callback(
    callback: Callable[[HookFiber | None, UpdatePriority], None] | None,
) -> None:
    global _schedule_update_callback
    _schedule_update_callback = callback


def _set_rerender_callback(callback: Callable[[], None] | None) -> None:
    global _compat_rerender_callback, _compat_rerender_scheduled
    _compat_rerender_callback = callback
    _compat_rerender_scheduled = False


def _notify_compat_rerender_callback() -> None:
    global _compat_rerender_scheduled
    callback = _compat_rerender_callback
    if callback is None:
        return
    if _runtime.render_cycle_active and _runtime.batch_depth == 0:
        callback()
        return
    if _compat_rerender_scheduled:
        return
    _compat_rerender_scheduled = True

    def run_callback() -> None:
        global _compat_rerender_scheduled
        _compat_rerender_scheduled = False
        current_callback = _compat_rerender_callback
        if current_callback is not None:
            current_callback()

    if _runtime.render_cycle_active or _runtime.batch_depth > 0:
        _runtime.after_batch_callbacks.append(run_callback)
        return

    threading.Timer(0.001, run_callback).start()


def _priority_rank(priority: UpdatePriority) -> int:
    if priority == NoEventPriority:
        return 0
    return 1000 - priority


def _lane_to_mask(priority: UpdatePriority) -> int:
    if priority == DiscreteEventPriority:
        return 1 << 0
    if priority == DefaultEventPriority:
        return 1 << 1
    if priority == TransitionEventPriority:
        return 1 << 2
    return 1 << 3


def _merge_lanes(a: int, b: int) -> int:
    return a | b


def _get_highest_priority_lane(lanes: int) -> UpdatePriority:
    if (
        shared_internals.current_transition is not None
        and lanes & _lane_to_mask(TransitionEventPriority)
    ):
        return TransitionEventPriority
    if lanes & _lane_to_mask(DiscreteEventPriority):
        return DiscreteEventPriority
    if lanes & _lane_to_mask(DefaultEventPriority):
        return DefaultEventPriority
    if lanes & _lane_to_mask(TransitionEventPriority):
        return TransitionEventPriority
    return DefaultEventPriority if lanes != NoEventPriority else NoEventPriority


def _remove_lane(lanes: int, priority: UpdatePriority) -> int:
    return lanes & ~_lane_to_mask(priority)


def _queue_pending_rerender(
    priority: UpdatePriority,
    fiber: HookFiber | None = None,
    source: str | None = None,
) -> None:
    _notify_compat_rerender_callback()
    _runtime.rerender_pending = True
    _runtime.pending_update_lanes = _merge_lanes(
        _runtime.pending_update_lanes,
        _lane_to_mask(priority),
    )
    if fiber is not None and (
        _runtime.pending_fiber is None
        or _priority_rank(priority) >= _priority_rank(_runtime.pending_update_priority)
    ):
        _runtime.pending_fiber = fiber
    should_update_source = (
        _runtime.pending_update_source is None
        or _priority_rank(priority) >= _priority_rank(_runtime.pending_update_priority)
    )
    _runtime.pending_update_priority = higherEventPriority(
        priority,
        _runtime.pending_update_priority,
    )
    if should_update_source:
        _runtime.pending_update_source = source


def _consume_pending_rerender_priority_numeric() -> UpdatePriority | None:
    if not _runtime.rerender_pending:
        return None
    priority = _get_highest_priority_lane(_runtime.pending_update_lanes)
    _runtime.pending_update_lanes = _remove_lane(_runtime.pending_update_lanes, priority)
    _runtime.rerender_pending = _runtime.pending_update_lanes != NoEventPriority
    _runtime.pending_update_priority = _get_highest_priority_lane(_runtime.pending_update_lanes)
    if not _runtime.rerender_pending:
        _runtime.pending_update_source = None
    return priority


def _consume_pending_rerender_priority() -> str | None:
    source = _runtime.pending_update_source
    priority = _consume_pending_rerender_priority_numeric()
    if priority is None:
        return None
    if source is not None:
        return source
    if priority == RenderPhaseUpdatePriority:
        return "render_phase"
    if priority == DefaultEventPriority:
        return "default"
    if priority == TransitionEventPriority:
        return "transition"
    return "default"


def _has_pending_rerender() -> bool:
    return _runtime.rerender_pending


def _has_rerender_target() -> bool:
    return (
        _schedule_update_callback is not None
        or _runtime.render_cycle_active
        or _runtime.batch_depth > 0
    )


def _override_hook_state(
    instance_id: str,
    path: list[Any],
    value: Any,
) -> bool:
    if not path:
        return False
    fiber = _runtime.fibers.get(instance_id)
    if fiber is None:
        return False
    hook_index = path[0]
    hook = _get_hook_node_by_index(fiber, hook_index) if isinstance(hook_index, int) else None
    if hook is None or hook.memoized_state is _UNSET:
        return False
    if len(path) == 1:
        hook.memoized_state = _clone_hook_value(value)
        queue = hook.queue
        if queue is not None:
            queue.last_rendered_state = hook.memoized_state
        return True
    target = hook.memoized_state
    return _set_nested_value(target, path[1:], value)


def _get_hook_state_snapshot(instance_id: str) -> list[dict[str, Any]] | None:
    fiber = next(
        (item for item in reversed(_runtime.fiber_stack) if item.component_id == instance_id),
        None,
    )
    if fiber is None:
        fiber = _runtime.fibers.get(instance_id)
    if fiber is None:
        return None

    snapshot: list[dict[str, Any]] = []
    current = fiber.hook_head
    while current is not None:
        kind = current.kind
        value: Any = None
        if current.memoized_state is not _UNSET:
            value = _clone_hook_value(current.memoized_state)
        elif current.ref is not None:
            value = {"current": _clone_hook_value(getattr(current.ref, "current", None))}
        elif current.memoized_value is not _UNSET:
            value = _clone_hook_value(current.memoized_value)

        snapshot.append(
            {
                "id": current.index,
                "name": kind,
                "value": value,
                "isStateEditable": kind in ("State", "Reducer"),
            }
        )
        current = current.next

    return snapshot


def _delete_hook_state_path(
    instance_id: str,
    path: list[Any],
) -> bool:
    if len(path) < 2:
        return False
    fiber = _runtime.fibers.get(instance_id)
    if fiber is None:
        return False
    hook_index = path[0]
    hook = _get_hook_node_by_index(fiber, hook_index) if isinstance(hook_index, int) else None
    if hook is None or hook.memoized_state is _UNSET:
        return False
    return _delete_nested_value(hook.memoized_state, path[1:])


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
    fiber = _runtime.fibers.get(instance_id)
    if fiber is None:
        return False
    hook_index = old_path[0]
    hook = _get_hook_node_by_index(fiber, hook_index) if isinstance(hook_index, int) else None
    if hook is None or hook.memoized_state is _UNSET:
        return False
    target = hook.memoized_state
    value, found = _pop_nested_value(target, old_path[1:])
    if not found:
        return False
    return _set_nested_value(target, new_path[1:], value)


def _request_rerender(
    fiber: HookFiber | None = None,
    *,
    priority: UpdatePriority | None = None,
) -> None:
    resolved_priority = priority or _get_current_update_priority()

    _queue_pending_rerender(
        resolved_priority,
        fiber=fiber,
        source=_get_current_update_source() if priority is None else None,
    )

    if _runtime.render_cycle_active:
        return

    if _runtime.batch_depth > 0:
        return

    if (
        _schedule_update_callback is not None
        and resolved_priority > DiscreteEventPriority
    ):
        _schedule_update_flush()
        return

    _flush_scheduled_rerender()


def _flush_batched_rerender() -> None:
    if not _has_pending_rerender():
        return
    if _runtime.render_cycle_active:
        return
    _flush_scheduled_rerender()


def _run_after_batch_callbacks() -> None:
    callbacks = _runtime.after_batch_callbacks[:]
    _runtime.after_batch_callbacks.clear()
    for callback in callbacks:
        with suppress(Exception):
            callback()


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
    previous = shared_internals.current_update_priority
    shared_internals.current_update_priority = DiscreteEventPriority
    try:
        return _batched_updates_runtime(callback)
    finally:
        shared_internals.current_update_priority = previous


def useState(
    initial_value: T | Callable[[], T],
) -> tuple[T, Callable[[T | Callable[[T], T]], None]]:
    fiber = _get_current_fiber()
    hook = _get_or_create_hook(fiber, "State")
    value = initial_value() if callable(initial_value) else initial_value
    current_value, queue = _process_hook_queue(
        hook,
        _basic_state_reducer,
        value,
        fiber,
    )

    if queue.dispatch is None:
        queue.dispatch = _create_hook_dispatch(hook, queue, fiber)
    return (current_value, queue.dispatch)


def _use_hook_effect(
    effect: Callable[[], Callable[[], None] | None],
    deps: Deps | None,
    *,
    fiber_flag: int,
    hook_flags: int,
) -> None:
    fiber = _get_current_fiber()
    fiber.flags |= fiber_flag
    hook = _get_or_create_hook(fiber, "Effect")
    normalized_deps = _normalize_deps(deps)
    if hook.deps is not None and not _deps_changed(hook.deps, normalized_deps):
        return
    if _runtime.render_cycle_active and _runtime.fiber_stack:
        _runtime.pending_effects.append(
            PendingEffect(
                instance_id=_get_current_instance_id(),
                hook_index=hook.index,
                hook_flags=hook_flags,
                effect=effect,
                deps=normalized_deps,
            )
        )
        return
    _run_cleanup(hook.cleanup)
    cleanup = effect()
    hook.deps = normalized_deps
    hook.cleanup = cleanup


def useEffect(
    effect: Callable[[], Callable[[], None] | None],
    deps: Deps | None = None,
) -> None:
    _use_hook_effect(
        effect,
        deps,
        fiber_flag=Passive,
        hook_flags=HookPassive,
    )


def useLayoutEffect(
    effect: Callable[[], Callable[[], None] | None],
    deps: Deps | None = None,
) -> None:
    from pyinkcli.packages.react_reconciler.ReactFiberFlags import Callback

    _use_hook_effect(
        effect,
        deps,
        fiber_flag=Callback,
        hook_flags=HookLayout,
    )


def useInsertionEffect(
    effect: Callable[[], Callable[[], None] | None],
    deps: Deps | None = None,
) -> None:
    from pyinkcli.packages.react_reconciler.ReactFiberFlags import Insertion

    _use_hook_effect(
        effect,
        deps,
        fiber_flag=Insertion,
        hook_flags=HookInsertion,
    )


def useRef(initial_value: T | None = None) -> Ref[T]:
    fiber = _get_current_fiber()
    hook = _get_or_create_hook(fiber, "Ref")
    if hook.ref is None:
        hook.ref = Ref(initial_value)
    return hook.ref


def useMemo(factory: Callable[[], T], deps: Deps) -> T:
    fiber = _get_current_fiber()
    hook = _get_or_create_hook(fiber, "Memo")
    normalized_deps = tuple(deps)
    if hook.memoized_value is not _UNSET and not _deps_changed(
        hook.memoized_deps,
        normalized_deps,
    ):
        return hook.memoized_value
    new_value = factory()
    hook.memoized_value = new_value
    hook.memoized_deps = normalized_deps
    return new_value


def useCallback(callback: Callable, deps: Deps) -> Callable:
    value = useMemo(lambda: callback, deps)
    fiber = _get_current_fiber()
    hook = _get_hook_node_by_index(fiber, fiber.index - 1)
    if hook is not None:
        hook.kind = "Callback"
    return value


def useReducer(
    reducer: Callable[[T, Any], T],
    initial_state: T,
    init: Callable[[T], T] | None = None,
) -> tuple[T, Callable[[Any], None]]:
    fiber = _get_current_fiber()
    hook = _get_or_create_hook(fiber, "Reducer")
    resolved_initial_state = init(initial_state) if init is not None else initial_state
    current_value, queue = _process_hook_queue(
        hook,
        reducer,
        resolved_initial_state,
        fiber,
    )

    if queue.dispatch is None:
        queue.dispatch = _create_hook_dispatch(hook, queue, fiber)
    return (current_value, queue.dispatch)


def useTransition() -> tuple[bool, Callable[[Callable[[], None]], None]]:
    is_pending, set_is_pending = useState(False)
    pending_count_ref = useRef(0)
    app_context = _get_app_context()

    def complete_transition() -> None:
        pending_count = pending_count_ref.current or 0
        pending_count = max(0, pending_count - 1)
        pending_count_ref.current = pending_count
        if pending_count == 0:
            set_is_pending(False)

    def run_transition(callback: Callable[[], None]) -> None:
        previous_transition = shared_internals.current_transition
        shared_internals.current_transition = object()
        try:
            _batched_updates_runtime(callback)
        finally:
            shared_internals.current_transition = previous_transition

    def start_transition(callback: Callable[[], None]) -> None:
        is_concurrent = bool(
            app_context is not None
            and getattr(getattr(app_context, "app", None), "is_concurrent", False)
        )
        if not is_concurrent:
            run_transition(callback)
            return

        pending_count_ref.current = (pending_count_ref.current or 0) + 1
        set_is_pending(True)

        def run_scheduled_transition() -> None:
            try:
                run_transition(callback)
            finally:
                complete_transition()

        _queue_after_current_batch(run_scheduled_transition)

    return (is_pending, start_transition)


__all__ = [
    "HookHasEffect",
    "HookInsertion",
    "HookLayout",
    "HookPassive",
    "HookFiber",
    "useState",
    "useEffect",
    "useInsertionEffect",
    "useLayoutEffect",
    "useRef",
    "useMemo",
    "useCallback",
    "useReducer",
    "useTransition",
    "Ref",
    "_set_current_hook_fiber",
    "_set_rerender_callback",
    "_get_hook_state_snapshot",
    "_override_hook_state",
    "_delete_hook_state_path",
    "_rename_hook_state_path",
]
