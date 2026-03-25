"""
React Fiber Lane 优先级模型 - 31 位位掩码系统

Lane 使用 31 位二进制数表示优先级，每个 bit 代表一个优先级。
数值越小，优先级越高（bit 位置越靠右优先级越高）。
"""

from __future__ import annotations

from typing import Union

# Lane 类型别名
Lane = int
Lanes = int

# =============================================================================
# Lane 常量定义 (31 位模型，与 React 18 对齐)
# =============================================================================

NoLanes = 0b0000000000000000000000000000000
NoLane = 0b0000000000000000000000000000000

# 同步优先级 - 最高优先级，用于用户交互和关键更新
SyncHydrationLane = 0b0000000000000000000000000000001  # bit 0
SyncLane = 0b0000000000000000000000000000010  # bit 1

# 输入连续优先级 - 用于连续的用户输入
InputContinuousHydrationLane = 0b0000000000000000000000000000100  # bit 2
InputContinuousLane = 0b0000000000000000000000000001000  # bit 3

# 默认优先级 - 普通更新
DefaultHydrationLane = 0b0000000000000000000000000010000  # bit 4
DefaultLane = 0b0000000000000000000000000100000  # bit 5

# 手势过渡优先级
GestureLane = 0b0000000000000000000000001000000  # bit 6

# 过渡优先级 (共 14 个 lane) - 用于低优先级的过渡更新
TransitionLane1 = 0b0000000000000000000000010000000  # bit 7
TransitionLane2 = 0b0000000000000000000000100000000  # bit 8
TransitionLane3 = 0b0000000000000000000001000000000  # bit 9
TransitionLane4 = 0b0000000000000000000010000000000  # bit 10
TransitionLane5 = 0b0000000000000000000100000000000  # bit 11
TransitionLane6 = 0b0000000000000000001000000000000  # bit 12
TransitionLane7 = 0b0000000000000000010000000000000  # bit 13
TransitionLane8 = 0b0000000000000000100000000000000  # bit 14
TransitionLane9 = 0b0000000000000001000000000000000  # bit 15
TransitionLane10 = 0b0000000000000010000000000000000  # bit 16
TransitionLane11 = 0b0000000000000100000000000000000  # bit 17
TransitionLane12 = 0b0000000000001000000000000000000  # bit 18
TransitionLane13 = 0b0000000000010000000000000000000  # bit 19
TransitionLane14 = 0b0000000000100000000000000000000  # bit 20

# 重试优先级 (共 4 个 lane) - 用于 Suspense 重试
RetryLane1 = 0b0000000001000000000000000000000  # bit 21
RetryLane2 = 0b0000000010000000000000000000000  # bit 22
RetryLane3 = 0b0000000100000000000000000000000  # bit 23
RetryLane4 = 0b0000001000000000000000000000000  # bit 24

# 空闲优先级 - 最低优先级，用于后台任务
IdleLane = 0b0010000000000000000000000000000  # bit 25

# 离屏渲染优先级 - 用于 Offscreen 组件
OffscreenLane = 0b0100000000000000000000000000000  # bit 26

# 延迟优先级 - 用于可延迟的更新
DeferredLane = 0b1000000000000000000000000000000  # bit 27

# =============================================================================
# Lane 组合常量
# =============================================================================

# 所有 Transition Lanes
TransitionLanes = (
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

# 所有 Retry Lanes
RetryLanes = RetryLane1 | RetryLane2 | RetryLane3 | RetryLane4

# 所有 Transition Update Lanes (用于循环分配)
TransitionUpdateLanes = TransitionLanes

# 所有非空闲 Lanes
NonIdleLanes = (
    SyncHydrationLane
    | SyncLane
    | InputContinuousHydrationLane
    | InputContinuousLane
    | DefaultHydrationLane
    | DefaultLane
    | GestureLane
    | TransitionLanes
    | RetryLanes
)

# 所有 Lanes (用于迭代)
TotalLanes = 28  # 使用的总位数

# =============================================================================
# Lane 位运算核心函数
# =============================================================================


def laneToMask(lane: int) -> int:
    """
    将单个 lane 转换为位掩码

    在这个实现中，lane 本身就是位掩码形式，所以直接返回。
    这个函数存在是为了与 React API 保持一致。

    Args:
        lane: 单个 lane 优先级

    Returns:
        对应的位掩码
    """
    return lane


def mergeLanes(a: int, b: int) -> int:
    """
    合并两个 lanes
    使用按位或运算
    """
    return a | b


def removeLanes(a: int, b: int) -> int:
    """
    从 a 中移除 b 包含的 lanes
    使用按位与非运算
    """
    return a & ~b


def getHighestPriorityLane(lanes: int) -> int:
    """
    获取最高优先级的 lane（最低位的 1）

    位运算技巧：lanes & -lanes 可以提取最低位的 1
    例如：0b110 & -0b110 = 0b010
    """
    if lanes == NoLanes:
        return NoLane
    return lanes & -lanes


def pick_arbitrary_lane(lanes: int) -> int:
    """
    从 lanes 中选择一个任意的 lane

    通常用于从一组 lanes 中选择一个来表示优先级。
    这里选择最高优先级的 lane（最低位的 1）。

    Args:
        lanes: lanes 位掩码

    Returns:
        单个 lane 或 NoLane
    """
    return getHighestPriorityLane(lanes)


def getLowestPriorityLane(lanes: int) -> int:
    """
    获取最低优先级的 lane（最高位的 1）
    """
    if lanes == NoLanes:
        return NoLane
    # 找到最高位的 1
    result = lanes
    while lanes > 0:
        result = lanes
        lanes = lanes >> 1
    return result


def includesSomeLane(a: int, b: int) -> bool:
    """
    检查 a 和 b 是否有共同的 lanes
    使用按位与运算
    """
    return (a & b) != NoLanes


def isSubsetOfLanes(set_lanes: int, subset: int) -> bool:
    """
    检查 subset 是否是 set_lanes 的子集
    """
    return (set_lanes & subset) == subset


def includesSyncLane(lanes: int) -> bool:
    """
    检查是否包含同步优先级
    """
    return (lanes & SyncLane) != NoLanes


def includesOnlyRetries(lanes: int) -> bool:
    """
    检查是否只包含重试 lanes
    """
    return lanes != NoLanes and (lanes & ~RetryLanes) == NoLanes


def includesOnlyTransitions(lanes: int) -> bool:
    """
    检查是否只包含过渡 lanes
    """
    return lanes != NoLanes and (lanes & ~TransitionLanes) == NoLanes


def includesNonIdleWork(lanes: int) -> bool:
    """
    检查是否包含非空闲工作
    """
    return (lanes & NonIdleLanes) != NoLanes


def includesBlockingLane(lanes: int) -> bool:
    """
    检查是否包含阻塞性 lane（同步或输入连续）
    """
    return (lanes & (SyncLane | InputContinuousLane)) != NoLanes


def includesExpiredLane(lanes: int) -> bool:
    """
    检查是否包含过期 lane
    简化实现：将 SyncLane 视为过期
    """
    return (lanes & SyncLane) != NoLanes


def includesTransitionLane(lanes: int) -> bool:
    """
    检查是否包含过渡 lane
    """
    return (lanes & TransitionLanes) != NoLanes


def includesIdleGroupLanes(lanes: int) -> bool:
    """
    检查是否包含空闲组 lanes
    """
    return (lanes & (IdleLane | OffscreenLane)) != NoLanes


def includesRetryLane(lanes: int) -> bool:
    """
    检查是否包含重试 lane
    """
    return (lanes & RetryLanes) != NoLanes


# =============================================================================
# Lane 优先级比较
# =============================================================================


def compareLanes(a: int, b: int) -> int:
    """
    比较两个 lanes 的优先级
    返回：
    - 负数：a 优先级高于 b
    - 0: 优先级相同
    - 正数：a 优先级低于 b
    """
    if a == b:
        return 0
    if a == NoLanes:
        return 1
    if b == NoLanes:
        return -1

    a_priority = getHighestPriorityLane(a)
    b_priority = getHighestPriorityLane(b)

    # 数值越小优先级越高
    if a_priority < b_priority:
        return -1
    elif a_priority > b_priority:
        return 1
    return 0


def higherPriorityLane(a: int, b: int) -> int:
    """
    返回优先级更高的 lane
    """
    if a == NoLanes:
        return b
    if b == NoLanes:
        return a
    if getHighestPriorityLane(a) < getHighestPriorityLane(b):
        return a
    return b


def lowerPriorityLane(a: int, b: int) -> int:
    """
    返回优先级更低的 lane
    """
    if a == NoLanes:
        return b
    if b == NoLanes:
        return a
    if getHighestPriorityLane(a) > getHighestPriorityLane(b):
        return a
    return b


# =============================================================================
# Lane 标签和调试
# =============================================================================


def getLabelForLane(lane: int) -> str:
    """
    获取 lane 的人类可读标签
    """
    labels = {
        SyncHydrationLane: "SyncHydration",
        SyncLane: "Sync",
        InputContinuousHydrationLane: "InputContinuousHydration",
        InputContinuousLane: "InputContinuous",
        DefaultHydrationLane: "DefaultHydration",
        DefaultLane: "Default",
        GestureLane: "Gesture",
        TransitionLane1: "Transition1",
        TransitionLane2: "Transition2",
        TransitionLane3: "Transition3",
        TransitionLane4: "Transition4",
        TransitionLane5: "Transition5",
        TransitionLane6: "Transition6",
        TransitionLane7: "Transition7",
        TransitionLane8: "Transition8",
        TransitionLane9: "Transition9",
        TransitionLane10: "Transition10",
        TransitionLane11: "Transition11",
        TransitionLane12: "Transition12",
        TransitionLane13: "Transition13",
        TransitionLane14: "Transition14",
        RetryLane1: "Retry1",
        RetryLane2: "Retry2",
        RetryLane3: "Retry3",
        RetryLane4: "Retry4",
        IdleLane: "Idle",
        OffscreenLane: "Offscreen",
        DeferredLane: "Deferred",
        NoLanes: "None",
    }
    return labels.get(lane, f"Unknown({bin(lane)})")


def getLanePriorityName(lanes: int) -> str:
    """
    获取 lanes 的优先级名称（用于调度）
    """
    if includesSyncLane(lanes):
        return "discrete"
    if includesSomeLane(lanes, InputContinuousLane):
        return "continuous"
    if includesSomeLane(lanes, DefaultLane):
        return "default"
    if includesTransitionLane(lanes):
        return "transition"
    if includesIdleGroupLanes(lanes):
        return "idle"
    return "unknown"


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    # 常量
    "NoLanes",
    "NoLane",
    "SyncHydrationLane",
    "SyncLane",
    "InputContinuousHydrationLane",
    "InputContinuousLane",
    "DefaultHydrationLane",
    "DefaultLane",
    "GestureLane",
    "TransitionLane1",
    "TransitionLane2",
    "TransitionLane3",
    "TransitionLane4",
    "TransitionLane5",
    "TransitionLane6",
    "TransitionLane7",
    "TransitionLane8",
    "TransitionLane9",
    "TransitionLane10",
    "TransitionLane11",
    "TransitionLane12",
    "TransitionLane13",
    "TransitionLane14",
    "RetryLane1",
    "RetryLane2",
    "RetryLane3",
    "RetryLane4",
    "IdleLane",
    "OffscreenLane",
    "DeferredLane",
    # 组合常量
    "TransitionLanes",
    "RetryLanes",
    "TransitionUpdateLanes",
    "NonIdleLanes",
    "TotalLanes",
    # 核心函数
    "laneToMask",
    "mergeLanes",
    "removeLanes",
    "getHighestPriorityLane",
    "pick_arbitrary_lane",
    "getLowestPriorityLane",
    "includesSomeLane",
    "isSubsetOfLanes",
    "includesSyncLane",
    "includesOnlyRetries",
    "includesOnlyTransitions",
    "includesNonIdleWork",
    "includesBlockingLane",
    "includesExpiredLane",
    "includesTransitionLane",
    "includesIdleGroupLanes",
    "includesRetryLane",
    # 比较函数
    "compareLanes",
    "higherPriorityLane",
    "lowerPriorityLane",
    # 调试函数
    "getLabelForLane",
    "getLanePriorityName",
]
