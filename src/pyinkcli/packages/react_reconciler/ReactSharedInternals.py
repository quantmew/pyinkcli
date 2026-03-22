from types import SimpleNamespace

from .ReactEventPriorities import DefaultEventPriority

shared_internals = SimpleNamespace(
    H=None,
    getCurrentStack=None,
    currentUpdatePriority=DefaultEventPriority,
    current_update_priority=DefaultEventPriority,
    current_transition=None,
)
