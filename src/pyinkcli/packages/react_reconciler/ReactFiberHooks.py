"""Reconciler-side hook dispatcher aligned with ReactFiberHooks responsibilities."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from pyinkcli._component_runtime import renderComponent
from pyinkcli.components._app_context_runtime import _get_app_context
from pyinkcli.hooks import _runtime
from pyinkcli.hooks._runtime import (
    HookNode,
    PendingEffect,
    Ref,
    _UNSET,
)
from pyinkcli.packages.react.dispatcher import (
    Dispatcher,
    getCurrentDispatcher,
    setCurrentDispatcher,
)
from pyinkcli.packages.react_reconciler.ReactFiberBeginWork import (
    markWorkInProgressReceivedUpdate,
    resetWorkInProgressReceivedUpdate,
)
from pyinkcli.packages.react_reconciler.ReactEventPriorities import (
    DefaultEventPriority,
)
from pyinkcli.packages.react_reconciler.ReactFiberFlags import Callback, Insertion, Passive
from pyinkcli.packages.react_reconciler.ReactFiberNewContext import readContext
from pyinkcli.packages.react_reconciler.ReactFiberNewContext import (
    checkIfContextChanged,
    finishReadingContext,
    prepareToReadContext,
)
from pyinkcli.packages.react_reconciler.ReactHookEffectTags import (
    Insertion as HookInsertion,
    Layout as HookLayout,
    Passive as HookPassive,
)
from pyinkcli.packages.react_reconciler.ReactSharedInternals import shared_internals

T = TypeVar("T")


def _use_context(context: Any) -> Any:
    return readContext(context)


def _use_state(
    initial_value: T | Callable[[], T],
) -> tuple[T, Callable[[T | Callable[[T], T]], None]]:
    fiber = _runtime._get_current_fiber()
    hook = _runtime._get_or_create_hook(fiber, "State")
    value = initial_value() if callable(initial_value) else initial_value
    current_value, queue = _runtime._process_hook_queue(
        hook,
        _runtime._basic_state_reducer,
        value,
        fiber,
    )
    if queue.dispatch is None:
        queue.dispatch = _runtime._create_hook_dispatch(hook, queue, fiber)
    return (current_value, queue.dispatch)


def _use_reducer(
    reducer: Callable[[T, Any], T],
    initial_state: T,
    init: Callable[[T], T] | None = None,
) -> tuple[T, Callable[[Any], None]]:
    fiber = _runtime._get_current_fiber()
    hook = _runtime._get_or_create_hook(fiber, "Reducer")
    resolved_initial_state = init(initial_state) if init is not None else initial_state
    current_value, queue = _runtime._process_hook_queue(
        hook,
        reducer,
        resolved_initial_state,
        fiber,
    )
    if queue.dispatch is None:
        queue.dispatch = _runtime._create_hook_dispatch(hook, queue, fiber)
    return (current_value, queue.dispatch)


def _use_hook_effect(
    effect: Callable[[], Callable[[], None] | None],
    deps: tuple[Any, ...] | None,
    *,
    fiber_flag: int,
    hook_flags: int,
) -> None:
    fiber = _runtime._get_current_fiber()
    fiber.flags |= fiber_flag
    hook = _runtime._get_or_create_hook(fiber, "Effect")
    normalized_deps = _runtime._normalize_deps(deps)
    if hook.deps is not None and not _runtime._deps_changed(hook.deps, normalized_deps):
        return
    if _runtime._runtime.render_cycle_active and _runtime._runtime.fiber_stack:
        _runtime._runtime.pending_effects.append(
            PendingEffect(
                instance_id=_runtime._get_current_instance_id(),
                hook_index=hook.index,
                hook_flags=hook_flags,
                effect=effect,
                deps=normalized_deps,
            )
        )
        return
    _runtime._run_cleanup(hook.cleanup)
    cleanup = effect()
    hook.deps = normalized_deps
    hook.cleanup = cleanup


def _use_effect(
    effect: Callable[[], Callable[[], None] | None],
    deps: tuple[Any, ...] | None = None,
) -> None:
    _use_hook_effect(effect, deps, fiber_flag=Passive, hook_flags=HookPassive)


def _use_layout_effect(
    effect: Callable[[], Callable[[], None] | None],
    deps: tuple[Any, ...] | None = None,
) -> None:
    _use_hook_effect(effect, deps, fiber_flag=Callback, hook_flags=HookLayout)


def _use_insertion_effect(
    effect: Callable[[], Callable[[], None] | None],
    deps: tuple[Any, ...] | None = None,
) -> None:
    _use_hook_effect(effect, deps, fiber_flag=Insertion, hook_flags=HookInsertion)


def _use_ref(initial_value: T | None = None) -> Ref[T]:
    fiber = _runtime._get_current_fiber()
    hook = _runtime._get_or_create_hook(fiber, "Ref")
    if hook.ref is None:
        hook.ref = Ref(initial_value)
    return hook.ref


def _use_memo(factory: Callable[[], T], deps: tuple[Any, ...]) -> T:
    fiber = _runtime._get_current_fiber()
    hook = _runtime._get_or_create_hook(fiber, "Memo")
    normalized_deps = tuple(deps)
    if hook.memoized_value is not _UNSET and not _runtime._deps_changed(
        hook.memoized_deps,
        normalized_deps,
    ):
        return hook.memoized_value
    new_value = factory()
    hook.memoized_value = new_value
    hook.memoized_deps = normalized_deps
    return new_value


def _use_callback(callback: Callable[..., T], deps: tuple[Any, ...]) -> Callable[..., T]:
    value = _use_memo(lambda: callback, deps)
    fiber = _runtime._get_current_fiber()
    hook = _runtime._get_hook_node_by_index(fiber, fiber.index - 1)
    if hook is not None:
        hook.kind = "Callback"
    return value


def _use_transition() -> tuple[bool, Callable[[Callable[[], None]], None]]:
    is_pending, set_is_pending = _use_state(False)
    pending_count_ref = _use_ref(0)
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
            _runtime._batched_updates_runtime(callback)
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

        _runtime._queue_after_current_batch(run_scheduled_transition)

    return (is_pending, start_transition)


class _HooksDispatcher:
    useContext = staticmethod(_use_context)
    useState = staticmethod(_use_state)
    useEffect = staticmethod(_use_effect)
    useLayoutEffect = staticmethod(_use_layout_effect)
    useInsertionEffect = staticmethod(_use_insertion_effect)
    useRef = staticmethod(_use_ref)
    useMemo = staticmethod(_use_memo)
    useCallback = staticmethod(_use_callback)
    useReducer = staticmethod(_use_reducer)
    useTransition = staticmethod(_use_transition)


HooksDispatcherOnMount: Dispatcher = _HooksDispatcher()
HooksDispatcherOnUpdate: Dispatcher = _HooksDispatcher()
HooksDispatcherOnRerender: Dispatcher = _HooksDispatcher()

_dispatcher_stack: list[Dispatcher | None] = []


def renderWithHooks(
    fiber: Any,
    component: Callable[..., Any],
    *children: Any,
    **props: Any,
) -> Any:
    previous_dispatcher = getCurrentDispatcher()
    _dispatcher_stack.append(previous_dispatcher)
    current = getattr(fiber, "alternate", None)
    is_update = current is not None and (
        getattr(current, "hook_head", None) is not None
        or getattr(current, "memoized_props", None) is not None
    )
    setCurrentDispatcher(HooksDispatcherOnUpdate if is_update else HooksDispatcherOnMount)
    resetWorkInProgressReceivedUpdate()
    if getattr(fiber, "memoized_props", None) != getattr(fiber, "pending_props", None):
        markWorkInProgressReceivedUpdate()
    if checkIfContextChanged(getattr(current, "dependencies", None)):
        markWorkInProgressReceivedUpdate()
    prepareToReadContext(fiber)
    try:
        return renderComponent(component, *children, **props)
    finally:
        finishReadingContext()


def finishRenderingHooks() -> None:
    previous_dispatcher = _dispatcher_stack.pop() if _dispatcher_stack else None
    setCurrentDispatcher(previous_dispatcher)


__all__ = [
    "HooksDispatcherOnMount",
    "HooksDispatcherOnRerender",
    "HooksDispatcherOnUpdate",
    "finishRenderingHooks",
    "renderWithHooks",
]
