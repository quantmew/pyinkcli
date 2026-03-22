"""Minimal lane helpers."""

from __future__ import annotations

from typing import TypeVar

Lane = int
Lanes = int

NoLanes: Lanes = 0
NoLane: Lane = 0

SyncHydrationLane: Lane = 1 << 0
SyncLane: Lane = 1 << 1
InputContinuousHydrationLane: Lane = 1 << 2
InputContinuousLane: Lane = 1 << 3
DefaultHydrationLane: Lane = 1 << 4
DefaultLane: Lane = 1 << 5
TransitionLane1: Lane = 1 << 6
TransitionLane2: Lane = 1 << 7
TransitionLane3: Lane = 1 << 8
TransitionLane4: Lane = 1 << 9
TransitionLane5: Lane = 1 << 10
TransitionLane6: Lane = 1 << 11
TransitionLane7: Lane = 1 << 12
TransitionLane8: Lane = 1 << 13
TransitionLane9: Lane = 1 << 14
TransitionLane10: Lane = 1 << 15
TransitionLane11: Lane = 1 << 16
TransitionLane12: Lane = 1 << 17
TransitionLane13: Lane = 1 << 18
TransitionLane14: Lane = 1 << 19
SelectiveHydrationLane: Lane = 1 << 20
IdleHydrationLane: Lane = 1 << 29
IdleLane: Lane = 1 << 30
OffscreenLane: Lane = 1 << 21
DeferredLane: Lane = 1 << 22
GestureLane: Lane = 1 << 23

SyncUpdateLanes: Lanes = SyncLane | InputContinuousLane | DefaultLane
UpdateLanes: Lanes = SyncLane | InputContinuousLane | DefaultLane | (
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
)

SomeTransitionLane: Lane = TransitionLane1
SomeRetryLane: Lane = 1 << 26


def mergeLanes(a: Lanes, b: Lanes) -> Lanes:
    return a | b


def removeLanes(lanes: Lanes, to_remove: Lanes) -> Lanes:
    return lanes & ~to_remove


def isSubsetOfLanes(set_of_lanes: Lanes, subset: Lanes) -> bool:
    return (set_of_lanes & subset) == subset


def includesSomeLane(a: Lanes, b: Lanes) -> bool:
    return (a & b) != 0


def includesSyncLane(lanes: Lanes) -> bool:
    return (lanes & SyncLane) != 0


def includesNonIdleWork(lanes: Lanes) -> bool:
    return (lanes & ~IdleLane) != 0


def getHighestPriorityLane(lanes: Lanes) -> Lane:
    return lanes & -lanes if lanes else NoLane


def pickArbitraryLane(lanes: Lanes) -> Lane:
    return getHighestPriorityLane(lanes)


def higherPriorityLane(a: Lane, b: Lane) -> Lane:
    if a == NoLane:
        return b
    if b == NoLane:
        return a
    return a if a < b else b


def higherPriorityLanes(a: Lanes, b: Lanes) -> Lanes:
    lane = higherPriorityLane(getHighestPriorityLane(a), getHighestPriorityLane(b))
    return lane


def getNextLanes(lanes: Lanes, _wip: Lanes | None = None) -> Lanes:
    return lanes


def getEntangledLanes(_root: object) -> Lanes:
    return NoLanes


def getLanesToRetrySynchronouslyOnError(_root: object) -> Lanes:
    return NoLanes


def upgradePendingLanesToSync(lanes: Lanes) -> Lanes:
    return lanes | SyncLane


def getHighestPriorityPendingLanes(lanes: Lanes) -> Lanes:
    return getHighestPriorityLane(lanes)


def markRootUpdated(*_args: object, **_kwargs: object) -> None:
    return None


def markRootFinished(*_args: object, **_kwargs: object) -> None:
    return None


def markRootPinged(*_args: object, **_kwargs: object) -> None:
    return None


def markRootSuspended(*_args: object, **_kwargs: object) -> None:
    return None


def markStarvedLanesAsExpired(*_args: object, **_kwargs: object) -> None:
    return None


def claimNextTransitionUpdateLane(*_args: object, **_kwargs: object) -> Lane:
    return TransitionLane1


def claimNextRetryLane(*_args: object, **_kwargs: object) -> Lane:
    return SomeRetryLane


def getNextLanesToFlushSync(_root: object, lanes: Lanes) -> Lanes:
    return lanes


def checkIfRootIsPrerendering(_root: object) -> bool:
    return False


def isGestureRender(_root: object) -> bool:
    return False


def includesOnlyViewTransitionEligibleLanes(_lanes: Lanes) -> bool:
    return False


def includesOnlyRetries(_lanes: Lanes) -> bool:
    return False


def includesOnlyTransitions(_lanes: Lanes) -> bool:
    return False


def includesBlockingLane(_lanes: Lanes) -> bool:
    return False


def includesTransitionLane(lanes: Lanes) -> bool:
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
    return (lanes & transition_mask) != 0


def includesRetryLane(_lanes: Lanes) -> bool:
    return False


def includesIdleGroupLanes(lanes: Lanes) -> bool:
    return (lanes & IdleLane) != 0


def includesExpiredLane(_lanes: Lanes) -> bool:
    return False


def getBumpedLaneForHydrationByLane(lane: Lane) -> Lane:
    return lane


def claimNextTransitionDeferredLane(*_args: object, **_kwargs: object) -> Lane:
    return TransitionLane11


def getTransitionsForLanes(_root: object, _lanes: Lanes) -> object | None:
    return None


def addFiberToLanesMap(*_args: object, **_kwargs: object) -> None:
    return None


def movePendingFibersToMemoized(*_args: object, **_kwargs: object) -> None:
    return None


def addTransitionToLanesMap(*_args: object, **_kwargs: object) -> None:
    return None


def getLabelForLane(lane: Lane) -> str | None:
    mapping = {
        SyncLane: "Sync",
        InputContinuousLane: "InputContinuous",
        DefaultLane: "Default",
        IdleLane: "Idle",
    }
    return mapping.get(lane)


NoTimestamp = -1

__all__ = [
    "Lane",
    "Lanes",
    "NoLanes",
    "NoLane",
    "SyncHydrationLane",
    "SyncLane",
    "InputContinuousHydrationLane",
    "InputContinuousLane",
    "DefaultHydrationLane",
    "DefaultLane",
    "GestureLane",
    "SelectiveHydrationLane",
    "IdleHydrationLane",
    "IdleLane",
    "OffscreenLane",
    "DeferredLane",
    "SomeTransitionLane",
    "SomeRetryLane",
    "SyncUpdateLanes",
    "UpdateLanes",
    "mergeLanes",
    "removeLanes",
    "isSubsetOfLanes",
    "includesSomeLane",
    "includesSyncLane",
    "includesNonIdleWork",
    "getHighestPriorityLane",
    "pickArbitraryLane",
    "higherPriorityLane",
    "higherPriorityLanes",
    "getNextLanes",
    "getEntangledLanes",
    "getLanesToRetrySynchronouslyOnError",
    "upgradePendingLanesToSync",
    "getHighestPriorityPendingLanes",
    "markRootUpdated",
    "markRootFinished",
    "markRootPinged",
    "markRootSuspended",
    "markStarvedLanesAsExpired",
    "claimNextTransitionUpdateLane",
    "claimNextRetryLane",
    "getNextLanesToFlushSync",
    "checkIfRootIsPrerendering",
    "isGestureRender",
    "includesOnlyViewTransitionEligibleLanes",
    "includesOnlyRetries",
    "includesOnlyTransitions",
    "includesBlockingLane",
    "includesTransitionLane",
    "includesRetryLane",
    "includesIdleGroupLanes",
    "includesExpiredLane",
    "getBumpedLaneForHydrationByLane",
    "claimNextTransitionDeferredLane",
    "getTransitionsForLanes",
    "addFiberToLanesMap",
    "movePendingFibersToMemoized",
    "addTransitionToLanesMap",
    "getLabelForLane",
    "NoTimestamp",
]
