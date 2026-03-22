NoLanes = 0
SyncLane = 1 << 0
InputContinuousLane = 1 << 1
DefaultLane = 1 << 2
TransitionLane1 = 1 << 3
IdleLane = 1 << 4


def mergeLanes(a: int, b: int) -> int:
    return a | b


def removeLanes(a: int, b: int) -> int:
    return a & ~b


def getHighestPriorityLane(lanes: int) -> int:
    return lanes & -lanes if lanes else NoLanes


def getLabelForLane(lane: int) -> str:
    return {
        SyncLane: "Sync",
        InputContinuousLane: "InputContinuous",
        DefaultLane: "Default",
        TransitionLane1: "Transition",
        IdleLane: "Idle",
        NoLanes: "None",
    }.get(lane, "Unknown")

