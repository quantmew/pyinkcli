"""React-style event priority surface for the pyinkcli reconciler."""

from __future__ import annotations

EventPriority = int
UpdatePriority = EventPriority

NoEventPriority: EventPriority = 0
DiscreteEventPriority: EventPriority = 1
DefaultEventPriority: EventPriority = 16
TransitionEventPriority: EventPriority = 32
IdleEventPriority: EventPriority = 64

# pyinkcli does not yet model render lanes. Use the sync/discrete lane as the
# temporary equivalent for render-phase updates until the hook queue is migrated.
RenderPhaseUpdatePriority: EventPriority = DiscreteEventPriority


def higherEventPriority(a: EventPriority, b: EventPriority) -> EventPriority:
    if a == NoEventPriority:
        return b
    if b == NoEventPriority:
        return a
    return a if a < b else b


def lowerEventPriority(a: EventPriority, b: EventPriority) -> EventPriority:
    if a == NoEventPriority:
        return b
    if b == NoEventPriority:
        return a
    return a if a > b else b


def isHigherEventPriority(a: EventPriority, b: EventPriority) -> bool:
    return a != NoEventPriority and (b == NoEventPriority or a < b)


def eventPriorityToLane(update_priority: EventPriority) -> int:
    return update_priority


def lanesToEventPriority(lanes: int) -> EventPriority:
    if lanes == NoEventPriority:
        return DefaultEventPriority
    if lanes <= DiscreteEventPriority:
        return DiscreteEventPriority
    if lanes <= DefaultEventPriority:
        return DefaultEventPriority
    if lanes <= TransitionEventPriority:
        return TransitionEventPriority
    return IdleEventPriority


__all__ = [
    "DefaultEventPriority",
    "DiscreteEventPriority",
    "EventPriority",
    "IdleEventPriority",
    "NoEventPriority",
    "RenderPhaseUpdatePriority",
    "TransitionEventPriority",
    "UpdatePriority",
    "eventPriorityToLane",
    "higherEventPriority",
    "isHigherEventPriority",
    "lanesToEventPriority",
    "lowerEventPriority",
]
