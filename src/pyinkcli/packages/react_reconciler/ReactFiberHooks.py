from __future__ import annotations

from ...hooks import _runtime as hooks_runtime
from . import ReactFiberNewContext as new_context
from .ReactFiberBeginWork import _mark_received_update
from .ReactSharedInternals import shared_internals

HooksDispatcherOnMount = object()
HooksDispatcherOnUpdate = object()
_previous_dispatcher = None


def renderWithHooks(fiber, component, *args, **kwargs):
    global _previous_dispatcher
    _previous_dispatcher = shared_internals.H
    is_update = bool(getattr(getattr(fiber, "alternate", None), "hook_head", None))
    shared_internals.H = HooksDispatcherOnUpdate if is_update else HooksDispatcherOnMount
    changed = getattr(fiber, "pending_props", None) != getattr(fiber, "memoized_props", None)
    changed = changed or new_context.checkIfContextChanged(getattr(getattr(fiber, "alternate", None), "dependencies", []))
    _mark_received_update(changed)
    new_context.prepareToReadContext(fiber)
    previous_use_context = hooks_runtime.useContext
    hooks_runtime.useContext = new_context.readContext
    try:
        return component(*args, **kwargs)
    finally:
        hooks_runtime.useContext = previous_use_context
        new_context.finishReadingContext()


def finishRenderingHooks() -> None:
    global _previous_dispatcher
    shared_internals.H = _previous_dispatcher
