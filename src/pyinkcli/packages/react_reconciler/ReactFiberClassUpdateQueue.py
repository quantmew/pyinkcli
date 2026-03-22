"""Minimal class update queue aligned with ReactFiberClassUpdateQueue responsibilities."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pyinkcli.packages.react_reconciler.ReactEventPriorities import (
    DefaultEventPriority,
    NoEventPriority,
)
from pyinkcli.packages.react_reconciler.ReactFiberConcurrentUpdates import (
    enqueueConcurrentClassUpdate,
    markFiberUpdated,
    unsafe_markUpdateLaneFromFiberToRoot,
)
from pyinkcli.packages.react_reconciler.ReactSharedInternals import shared_internals

UpdateState = 0
ReplaceState = 1
ForceUpdate = 2
CaptureUpdate = 3


def _get_current_update_priority() -> int:
    current_transition = shared_internals.current_transition
    if current_transition is not None:
        return getattr(shared_internals, "current_update_priority", DefaultEventPriority) or DefaultEventPriority
    return shared_internals.current_update_priority or DefaultEventPriority


def initializeUpdateQueue(instance: Any) -> None:
    setattr(instance, "_class_update_queue", [])
    setattr(instance, "_class_has_force_update", False)


def createUpdate(lane: int) -> dict[str, Any]:
    return {
        "lane": lane,
        "tag": UpdateState,
        "payload": None,
        "callback": None,
        "next": None,
    }


def enqueueUpdate(instance: Any, update: dict[str, Any], lane: int) -> Any:
    queue = getattr(instance, "_class_update_queue", None)
    if queue is None:
        initializeUpdateQueue(instance)
        queue = getattr(instance, "_class_update_queue")
    update["lane"] = lane
    queue.append(update)
    return instance


def processUpdateQueue(
    instance: Any,
    props: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool]:
    queue = list(getattr(instance, "_class_update_queue", ()))
    if not queue:
        return (dict(instance.state), bool(getattr(instance, "_class_has_force_update", False)))

    render_priority = shared_internals.current_render_priority or DefaultEventPriority
    next_state = dict(instance.state)
    applied_callbacks: list[Callable[[], Any]] = []
    remaining_updates: list[dict[str, Any]] = []
    has_force_update = bool(getattr(instance, "_class_has_force_update", False))

    if instance._pending_previous_state is None:
        instance._pending_previous_state = dict(instance.state)

    for update in queue:
        update_lane = int(update.get("lane", DefaultEventPriority) or DefaultEventPriority)
        if render_priority != NoEventPriority and update_lane > render_priority:
            remaining_updates.append(update)
            continue

        tag = update.get("tag", UpdateState)
        payload = update.get("payload")

        if tag == ReplaceState:
            if not isinstance(payload, dict):
                raise TypeError("replaceState expects a dict state payload.")
            next_state = dict(payload)
        elif tag == ForceUpdate:
            has_force_update = True
        else:
            partial_state: dict[str, Any] = {}
            if callable(payload):
                computed = payload(dict(next_state), dict(props or instance.props))
                if isinstance(computed, dict):
                    partial_state.update(computed)
            elif isinstance(payload, dict):
                partial_state.update(payload)
            elif payload is not None:
                raise TypeError(
                    "takes an object of state variables to update or a function which returns an object of state variables."
                )
            if partial_state:
                next_state.update(partial_state)

        callback = update.get("callback")
        if callable(callback):
            applied_callbacks.append(callback)

    instance.state = next_state
    instance._class_update_queue = remaining_updates
    instance._class_has_force_update = False
    if applied_callbacks:
        instance._react_update_callbacks.extend(applied_callbacks)

    if remaining_updates:
        from pyinkcli.packages.react.dispatcher import requestRerender

        requestRerender()

    return (next_state, has_force_update)


def createClassComponentUpdater(component_id: str):
    class _ClassComponentUpdater:
        @staticmethod
        def isMounted(publicInstance: Any) -> bool:
            return not getattr(publicInstance, "_is_unmounted", False) and bool(
                getattr(publicInstance, "_is_mounted", False)
            )

        @staticmethod
        def enqueueSetState(
            publicInstance: Any,
            partialState: Any,
            callback: Callable[[], Any] | None = None,
            callerName: str | None = None,
        ) -> None:
            del callerName
            if getattr(publicInstance, "_is_unmounted", False):
                return
            update = createUpdate(_get_current_update_priority())
            update["tag"] = UpdateState
            update["payload"] = partialState
            update["callback"] = callback
            enqueueUpdate(publicInstance, update, update["lane"])
            source_fiber = getattr(publicInstance, "_react_internal_fiber", publicInstance)
            enqueueConcurrentClassUpdate(source_fiber, publicInstance, update, update["lane"])
            markFiberUpdated(source_fiber, update["lane"])
            unsafe_markUpdateLaneFromFiberToRoot(source_fiber, update["lane"])
            from pyinkcli.packages.react.dispatcher import requestRerender

            requestRerender()

        @staticmethod
        def enqueueReplaceState(
            publicInstance: Any,
            completeState: Any,
            callback: Callable[[], Any] | None = None,
            callerName: str | None = None,
        ) -> None:
            del callerName
            if getattr(publicInstance, "_is_unmounted", False):
                return
            update = createUpdate(_get_current_update_priority())
            update["tag"] = ReplaceState
            update["payload"] = completeState
            update["callback"] = callback
            enqueueUpdate(publicInstance, update, update["lane"])
            source_fiber = getattr(publicInstance, "_react_internal_fiber", publicInstance)
            enqueueConcurrentClassUpdate(source_fiber, publicInstance, update, update["lane"])
            markFiberUpdated(source_fiber, update["lane"])
            unsafe_markUpdateLaneFromFiberToRoot(source_fiber, update["lane"])
            from pyinkcli.packages.react.dispatcher import requestRerender

            requestRerender()

        @staticmethod
        def enqueueForceUpdate(
            publicInstance: Any,
            callback: Callable[[], Any] | None = None,
            callerName: str | None = None,
        ) -> None:
            del callerName
            if getattr(publicInstance, "_is_unmounted", False):
                return
            update = createUpdate(_get_current_update_priority())
            update["tag"] = ForceUpdate
            update["callback"] = callback
            enqueueUpdate(publicInstance, update, update["lane"])
            source_fiber = getattr(publicInstance, "_react_internal_fiber", publicInstance)
            enqueueConcurrentClassUpdate(source_fiber, publicInstance, update, update["lane"])
            markFiberUpdated(source_fiber, update["lane"])
            unsafe_markUpdateLaneFromFiberToRoot(source_fiber, update["lane"])
            publicInstance._class_has_force_update = True
            from pyinkcli.packages.react.dispatcher import requestRerender

            requestRerender()

    _ClassComponentUpdater.component_id = component_id  # type: ignore[attr-defined]
    return _ClassComponentUpdater()


__all__ = [
    "CaptureUpdate",
    "ForceUpdate",
    "ReplaceState",
    "UpdateState",
    "createClassComponentUpdater",
    "createUpdate",
    "enqueueUpdate",
    "initializeUpdateQueue",
    "processUpdateQueue",
]
