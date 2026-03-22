"""React-style event priority surface for the pyinkcli reconciler."""

from __future__ import annotations

from pyinkcli.packages.react_reconciler.ReactFiberLane import (
    DefaultLane,
    IdleLane,
    InputContinuousLane,
    Lane,
    NoLane,
    SyncLane,
    TransitionLane1,
    getHighestPriorityLane,
)

EventPriority = int
UpdatePriority = EventPriority

NoEventPriority: EventPriority = 0
DiscreteEventPriority: EventPriority = SyncLane
ContinuousEventPriority: EventPriority = InputContinuousLane
DefaultEventPriority: EventPriority = DefaultLane
TransitionEventPriority: EventPriority = TransitionLane1
IdleEventPriority: EventPriority = IdleLane

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


def eventPriorityToLane(update_priority: EventPriority) -> Lane:
    return update_priority


def lanesToEventPriority(lanes: int) -> EventPriority:
    lane = getHighestPriorityLane(lanes)
    if lane == NoLane:
        return DefaultEventPriority
    if lane == DiscreteEventPriority:
        return DiscreteEventPriority
    if lane == ContinuousEventPriority:
        return ContinuousEventPriority
    if lane == DefaultEventPriority:
        return DefaultEventPriority
    if lane == TransitionEventPriority:
        return TransitionEventPriority
    return IdleEventPriority


__all__ = [
    "ContinuousEventPriority",
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
