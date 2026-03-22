"""Dispatcher and runtime bridge for the React compatibility layer."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol, TypeVar

from pyinkcli.hooks import _runtime
from pyinkcli.packages.react_reconciler.ReactSharedInternals import shared_internals

if TYPE_CHECKING:
    from pyinkcli.hooks._runtime import HookFiber

T = TypeVar("T")


class Dispatcher(Protocol):
    def useContext(self, context: Any) -> Any: ...
    def useState(self, initial_state: Any) -> Any: ...
    def useEffect(self, create: Callable[[], Any], deps: Any = None) -> Any: ...
    def useLayoutEffect(self, create: Callable[[], Any], deps: Any = None) -> Any: ...
    def useInsertionEffect(self, create: Callable[[], Any], deps: Any = None) -> Any: ...
    def useRef(self, initial_value: Any = None) -> Any: ...
    def useMemo(self, create: Callable[[], Any], deps: Any) -> Any: ...
    def useCallback(self, callback: Callable[..., Any], deps: Any) -> Any: ...
    def useReducer(self, reducer: Callable[[Any, Any], Any], initial_arg: Any, init: Callable[[Any], Any] | None = None) -> Any: ...
    def useTransition(self) -> Any: ...


class _RuntimeDispatcher:
    @staticmethod
    def useContext(context: Any) -> Any:
        getter = getattr(context, "get", None)
        if callable(getter):
            return getter()
        return getattr(context, "_currentValue", None)

    useState = staticmethod(_runtime.useState)
    useEffect = staticmethod(_runtime.useEffect)
    useLayoutEffect = staticmethod(_runtime.useLayoutEffect)
    useInsertionEffect = staticmethod(_runtime.useInsertionEffect)
    useRef = staticmethod(_runtime.useRef)
    useMemo = staticmethod(_runtime.useMemo)
    useCallback = staticmethod(_runtime.useCallback)
    useReducer = staticmethod(_runtime.useReducer)
    useTransition = staticmethod(_runtime.useTransition)


_default_dispatcher: Dispatcher = _RuntimeDispatcher()
_current_dispatcher: Dispatcher | None = _default_dispatcher
shared_internals.H = _current_dispatcher


def resolveDispatcher() -> Dispatcher:
    dispatcher = shared_internals.H
    if dispatcher is None:
        raise RuntimeError(
            "Invalid hook call. Hooks can only be called inside function components."
        )
    return dispatcher


def setCurrentDispatcher(dispatcher: Dispatcher | None) -> Dispatcher | None:
    global _current_dispatcher
    previous = _current_dispatcher
    _current_dispatcher = dispatcher
    shared_internals.H = dispatcher
    return previous


def getCurrentDispatcher() -> Dispatcher | None:
    return shared_internals.H


def resetCurrentDispatcher() -> Dispatcher:
    global _current_dispatcher
    _current_dispatcher = _default_dispatcher
    shared_internals.H = _default_dispatcher
    return _default_dispatcher


def requestRerender(fiber: HookFiber | None = None, *, priority: int | None = None) -> None:
    _runtime._request_rerender(fiber, priority=priority)


def hasRerenderTarget() -> bool:
    return _runtime._has_rerender_target()


def flushScheduledRerender() -> bool:
    return _runtime._flush_scheduled_rerender()


def setScheduleUpdateCallback(
    callback: Callable[[HookFiber | None, int], None] | None,
) -> None:
    _runtime._set_schedule_update_callback(callback)


def resetHookState() -> None:
    _runtime._reset_hook_state()


def clearHookState() -> None:
    _runtime._clear_hook_state()
    resetCurrentDispatcher()


def beginComponentRender(fiber_or_instance_id: HookFiber | str) -> HookFiber:
    return _runtime._begin_component_render(fiber_or_instance_id)


def setCurrentHookFiber(fiber: HookFiber | None) -> None:
    _runtime._set_current_hook_fiber(fiber)


def endComponentRender() -> HookFiber | None:
    return _runtime._end_component_render()


def getHookStateSnapshot(instance_id: str) -> list[dict[str, Any]] | None:
    return _runtime._get_hook_state_snapshot(instance_id)


def overrideHookState(instance_id: str, path: list[Any], value: Any) -> bool:
    return _runtime._override_hook_state(instance_id, path, value)


def deleteHookStatePath(instance_id: str, path: list[Any]) -> bool:
    return _runtime._delete_hook_state_path(instance_id, path)


def renameHookStatePath(instance_id: str, old_path: list[Any], new_path: list[Any]) -> bool:
    return _runtime._rename_hook_state_path(instance_id, old_path, new_path)


def batchedUpdatesRuntime(callback: Callable[[], T]) -> T:
    return _runtime._batched_updates_runtime(callback)


def queueAfterCurrentBatch(callback: Callable[[], None]) -> None:
    _runtime._queue_after_current_batch(callback)


def consumePendingRerenderPriority() -> str | None:
    return _runtime._consume_pending_rerender_priority()


__all__ = [
    "Dispatcher",
    "batchedUpdatesRuntime",
    "beginComponentRender",
    "clearHookState",
    "consumePendingRerenderPriority",
    "deleteHookStatePath",
    "endComponentRender",
    "flushScheduledRerender",
    "getCurrentDispatcher",
    "getHookStateSnapshot",
    "hasRerenderTarget",
    "overrideHookState",
    "queueAfterCurrentBatch",
    "renameHookStatePath",
    "requestRerender",
    "resetCurrentDispatcher",
    "resetHookState",
    "resolveDispatcher",
    "setCurrentDispatcher",
    "setCurrentHookFiber",
    "setScheduleUpdateCallback",
]
