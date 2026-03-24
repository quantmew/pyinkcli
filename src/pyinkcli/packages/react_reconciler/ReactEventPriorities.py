"""
React 事件优先级定义

将 Lane 优先级映射到事件优先级，用于调度器集成。
"""

from __future__ import annotations

from .ReactFiberLane import (
    SyncLane,
    InputContinuousLane,
    DefaultLane,
    TransitionLane1,
    IdleLane,
    NoLane,
)

# =============================================================================
# 事件优先级常量
# =============================================================================

# 离散事件优先级 - 最高优先级，用于点击、键盘等即时交互
DiscreteEventPriority = SyncLane

# 连续事件优先级 - 用于连续交互如拖拽、滚动
ContinuousEventPriority = InputContinuousLane

# 默认事件优先级 - 普通更新
DefaultEventPriority = DefaultLane

# 过渡事件优先级 - 低优先级过渡更新
TransitionEventPriority = TransitionLane1

# 空闲事件优先级 - 最低优先级
IdleEventPriority = IdleLane

# 无优先级
NoEventPriority = NoLane

# =============================================================================
# Lane 到事件优先级的映射
# =============================================================================


def lanesToEventPriority(lanes: int) -> int:
    """
    将 lanes 转换为事件优先级

    优先级顺序（从高到低）:
    Discrete > Continuous > Default > Transition > Idle
    """
    if lanes == NoLane:
        return NoEventPriority

    # 检查是否包含高优先级 lane
    if lanes & DiscreteEventPriority:
        return DiscreteEventPriority
    if lanes & ContinuousEventPriority:
        return ContinuousEventPriority
    if lanes & DefaultEventPriority:
        return DefaultEventPriority
    if lanes & TransitionEventPriority:
        return TransitionEventPriority
    if lanes & IdleEventPriority:
        return IdleEventPriority

    return DefaultEventPriority


def eventPriorityToLaneName(priority: int) -> str:
    """
    将事件优先级转换为人类可读的名称
    """
    if priority == DiscreteEventPriority:
        return "Discrete"
    if priority == ContinuousEventPriority:
        return "Continuous"
    if priority == DefaultEventPriority:
        return "Default"
    if priority == TransitionEventPriority:
        return "Transition"
    if priority == IdleEventPriority:
        return "Idle"
    return "Unknown"


# =============================================================================
# Scheduler 优先级映射 (用于与 JS Scheduler 对齐)
# =============================================================================

# Scheduler 优先级值（与 React Scheduler 对齐）
ImmediateSchedulerPriority = 0  # 对应 Discrete
UserBlockingSchedulerPriority = 1  # 对应 Continuous
NormalSchedulerPriority = 2  # 对应 Default
LowSchedulerPriority = 3  # 对应 Transition
IdleSchedulerPriority = 4  # 对应 Idle


def eventPriorityToSchedulerPriority(event_priority: int) -> int:
    """
    将事件优先级转换为 Scheduler 优先级
    """
    if event_priority == DiscreteEventPriority:
        return ImmediateSchedulerPriority
    if event_priority == ContinuousEventPriority:
        return UserBlockingSchedulerPriority
    if event_priority == DefaultEventPriority:
        return NormalSchedulerPriority
    if event_priority == TransitionEventPriority:
        return LowSchedulerPriority
    if event_priority == IdleEventPriority:
        return IdleSchedulerPriority
    return NormalSchedulerPriority


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    # 常量
    "DiscreteEventPriority",
    "ContinuousEventPriority",
    "DefaultEventPriority",
    "TransitionEventPriority",
    "IdleEventPriority",
    "NoEventPriority",
    # 转换函数
    "lanesToEventPriority",
    "eventPriorityToLaneName",
    # Scheduler 优先级
    "ImmediateSchedulerPriority",
    "UserBlockingSchedulerPriority",
    "NormalSchedulerPriority",
    "LowSchedulerPriority",
    "IdleSchedulerPriority",
    "eventPriorityToSchedulerPriority",
]
