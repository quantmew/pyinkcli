"""Lane helpers aligned with ReactFiberLane responsibilities."""

from __future__ import annotations

Lane = int
Lanes = int

TotalLanes = 4

NoLanes: Lanes = 0
NoLane: Lane = 0

SyncLane: Lane = 1 << 0
InputContinuousLane: Lane = 1 << 1
DefaultLane: Lane = 1 << 2
TransitionLane1: Lane = 1 << 3
IdleLane: Lane = 1 << 4

SyncUpdateLanes: Lanes = SyncLane | InputContinuousLane | DefaultLane
TransitionLanes: Lanes = TransitionLane1
SomeTransitionLane: Lane = TransitionLane1
NonIdleLanes: Lanes = SyncUpdateLanes | TransitionLanes


def getLabelForLane(lane: Lane) -> str | None:
    if lane == SyncLane:
        return "Sync"
    if lane == InputContinuousLane:
        return "InputContinuous"
    if lane == DefaultLane:
        return "Default"
    if lane == TransitionLane1:
        return "Transition"
    if lane == IdleLane:
        return "Idle"
    return None


def mergeLanes(a: Lanes, b: Lanes) -> Lanes:
    return a | b


def removeLanes(set_: Lanes, subset: Lanes) -> Lanes:
    return set_ & ~subset


def includesSomeLane(a: Lanes, b: Lanes) -> bool:
    return (a & b) != 0


def isSubsetOfLanes(set_: Lanes, subset: Lanes) -> bool:
    return (set_ & subset) == subset


def getHighestPriorityLane(lanes: Lanes) -> Lane:
    if lanes == NoLanes:
        return NoLane
    return lanes & -lanes


def getHighestPriorityLanes(lanes: Lanes | Lane) -> Lanes:
    highest = getHighestPriorityLane(int(lanes))
    if highest == NoLane:
        return NoLanes
    if highest in (SyncLane, InputContinuousLane, DefaultLane):
        return lanes & SyncUpdateLanes
    if highest == TransitionLane1:
        return lanes & TransitionLanes
    return highest


def laneToIndex(lane: Lane) -> int:
    if lane == NoLane:
        return -1
    return lane.bit_length() - 1


def markRootUpdated(root: object, updateLane: Lane) -> None:
    pending = getattr(root, "pending_lanes", NoLanes)
    setattr(root, "pending_lanes", mergeLanes(pending, updateLane))


__all__ = [
    "DefaultLane",
    "IdleLane",
    "InputContinuousLane",
    "Lane",
    "Lanes",
    "NoLane",
    "NoLanes",
    "NonIdleLanes",
    "SomeTransitionLane",
    "SyncLane",
    "SyncUpdateLanes",
    "TotalLanes",
    "TransitionLane1",
    "TransitionLanes",
    "getHighestPriorityLane",
    "getHighestPriorityLanes",
    "getLabelForLane",
    "includesSomeLane",
    "isSubsetOfLanes",
    "laneToIndex",
    "markRootUpdated",
    "mergeLanes",
    "removeLanes",
]
