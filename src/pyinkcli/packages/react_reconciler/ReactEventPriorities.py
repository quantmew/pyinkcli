"""Event priority helpers."""

from __future__ import annotations

from .ReactFiberLane import (
    DefaultLane,
    IdleLane,
    InputContinuousLane,
    NoLane,
    SyncLane,
    TransitionLane1,
    TransitionLane10,
    TransitionLane11,
    TransitionLane12,
    TransitionLane13,
    TransitionLane14,
    TransitionLane2,
    TransitionLane3,
    TransitionLane4,
    TransitionLane5,
    TransitionLane6,
    TransitionLane7,
    TransitionLane8,
    TransitionLane9,
    getHighestPriorityLane,
    includesNonIdleWork,
)

EventPriority = int
UpdatePriority = int

NoEventPriority: int = NoLane
DiscreteEventPriority: int = SyncLane
ContinuousEventPriority: int = InputContinuousLane
DefaultEventPriority: int = DefaultLane
IdleEventPriority: int = IdleLane
TransitionEventPriority: int = 1 << 27
RenderPhaseUpdatePriority: int = 1


def higherEventPriority(a: int, b: int) -> int:
    return a if a != 0 and a < b else b


def lowerEventPriority(a: int, b: int) -> int:
    return a if a == 0 or a > b else b


def isHigherEventPriority(a: int, b: int) -> bool:
    return a != 0 and a < b


def eventPriorityToLane(update_priority: int) -> int:
    if update_priority == TransitionEventPriority:
        return TransitionLane1
    return update_priority


def lanesToEventPriority(lanes: int) -> int:
    lane = getHighestPriorityLane(lanes)
    transition_mask = (
        TransitionLane1
        | TransitionLane2
        | TransitionLane3
        | TransitionLane4
        | TransitionLane5
        | TransitionLane6
        | TransitionLane7
        | TransitionLane8
        | TransitionLane9
        | TransitionLane10
        | TransitionLane11
        | TransitionLane12
        | TransitionLane13
        | TransitionLane14
    )
    if lane & transition_mask:
        return TransitionEventPriority
    if not isHigherEventPriority(DiscreteEventPriority, lane):
        return DiscreteEventPriority
    if not isHigherEventPriority(ContinuousEventPriority, lane):
        return ContinuousEventPriority
    if includesNonIdleWork(lane):
        return DefaultEventPriority
    return IdleEventPriority


__all__ = [
    "EventPriority",
    "UpdatePriority",
    "NoEventPriority",
    "DiscreteEventPriority",
    "ContinuousEventPriority",
    "DefaultEventPriority",
    "IdleEventPriority",
    "TransitionEventPriority",
    "RenderPhaseUpdatePriority",
    "higherEventPriority",
    "lowerEventPriority",
    "isHigherEventPriority",
    "eventPriorityToLane",
    "lanesToEventPriority",
]
