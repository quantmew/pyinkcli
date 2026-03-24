"""
React Fiber Root Scheduler - 根调度器

实现抢占式更新逻辑，处理多 Root 的优先级调度。
"""

from __future__ import annotations

from .ReactFiberLane import (
    DefaultLane,
    IdleLane,
    InputContinuousLane,
    NoLane,
    NoLanes,
    SyncLane,
    TransitionLanes,
    getHighestPriorityLane,
    includesBlockingLane,
    includesExpiredLane,
    includesSyncLane,
)
from .ReactEventPriorities import (
    DefaultEventPriority,
    DiscreteEventPriority,
    IdleEventPriority,
    TransitionEventPriority,
    eventPriorityToSchedulerPriority,
)

# =============================================================================
# 全局调度状态
# =============================================================================

# 第一个被调度的 Root (链表头)
firstScheduledRoot: object | None = None

# 最后一个被调度的 Root (链表尾)
lastScheduledRoot: object | None = None

# 是否已调度微任务
didScheduleMicrotask: bool = False

# 当前正在渲染的 Root
currentlyRenderingRoot: object | None = None

# 当前渲染的优先级
currentlyRenderingLane: int = NoLane

# 是否正在执行微任务回调
isExecutingMicrotask: bool = False

# =============================================================================
# getNextLanes - 获取下一个待处理的 Lanes
# =============================================================================


def getNextLanes(root: object, wipLanes: int, suspendedLanes: int = NoLanes) -> int:
    """
    获取下一个待处理的 Lanes (抢占式更新核心逻辑)

    算法：
    1. 检查是否有更高优先级的待处理工作
    2. 如果当前渲染被挂起，排除挂起的 lanes
    3. 返回最高优先级的非空 lanes

    Args:
        root: Fiber Root
        wipLanes: 当前 work-in-progress 的 lanes
        suspendedLanes: 被挂起的 lanes (Suspense)

    Returns:
        下一个待处理的 lanes，如果没有则返回 NoLanes
    """
    pendingLanes = getattr(root, "pending_lanes", NoLanes)

    if pendingLanes == NoLanes:
        return NoLanes

    # 排除被挂起的 lanes
    availableLanes = pendingLanes & ~suspendedLanes

    if availableLanes == NoLanes:
        return NoLanes

    # 获取最高优先级的 lane
    nextLane = getHighestPriorityLane(availableLanes)

    # 检查是否需要抢占当前渲染
    if wipLanes != NoLanes:
        # 数值越小优先级越高
        if nextLane < getHighestPriorityLane(wipLanes):
            # 有更高优先级的工作，需要抢占
            return nextLane
        # 否则继续当前渲染
        return wipLanes

    return nextLane


def getEntangledLanes(root: object, lane: int) -> int:
    """
    获取与指定 lane 纠缠在一起的所有 lanes

    某些 lanes 需要一起处理（如同步更新）
    """
    if lane == SyncLane:
        # 同步更新需要包含所有同步 lanes
        return getattr(root, "pending_lanes", NoLanes) & SyncLane
    return lane


# =============================================================================
# shouldTimeSlice - 判断是否应该使用时间切片
# =============================================================================


def shouldTimeSlice(root: object, lanes: int) -> bool:
    """
    判断是否应该使用时间切片（并发渲染）

    当不包含阻塞性 lane 且没有过期 lane 时，使用并发渲染
    """
    return (
        not includesBlockingLane(lanes)
        and not includesExpiredLane(lanes)
        and not _isRootPrerendering(root)
    )


def _isRootPrerendering(root: object) -> bool:
    """检查 root 是否处于预渲染模式"""
    return getattr(root, "is_prerendering", False)


# =============================================================================
# 调度队列管理
# =============================================================================


def scheduleImmediateRootScheduleTask() -> None:
    """
    调度立即的 Root 调度任务

    在微任务中处理所有待调度的 Root
    """
    from .ReactFiberWorkLoop import performWorkOnRoot

    # 使用异步方式调度
    import asyncio

    async def process_microtask():
        global isExecutingMicrotask
        isExecutingMicrotask = True
        try:
            processRootScheduleInMicrotask()
        finally:
            isExecutingMicrotask = False

    # 调度到事件循环
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(process_microtask())
    except RuntimeError:
        # 没有运行中的事件循环，创建新的
        loop = asyncio.new_event_loop()
        loop.run_until_complete(process_microtask())
        loop.close()


def ensureScheduleIsScheduled() -> None:
    """确保调度任务已被调度"""
    global didScheduleMicrotask
    if not didScheduleMicrotask:
        didScheduleMicrotask = True
        scheduleImmediateRootScheduleTask()


def resetRootSchedule() -> None:
    """重置 Root 调度状态"""
    global firstScheduledRoot, lastScheduledRoot, didScheduleMicrotask
    firstScheduledRoot = None
    lastScheduledRoot = None
    didScheduleMicrotask = False


# =============================================================================
# Root 调度模式
# =============================================================================


def getRootLaneFamily(root: object) -> str:
    """获取 Root 的 Lane 家族（用于调试）"""
    lanes = getattr(root, "pending_lanes", 0)
    if lanes & SyncLane:
        return "discrete"
    if lanes & InputContinuousLane:
        return "continuous"
    if lanes & DefaultLane:
        return "default"
    if lanes & TransitionLanes:
        return "transition"
    if lanes & IdleLane:
        return "idle"
    return "unknown"


def getRootScheduleMode(root: object) -> str:
    """
    获取 Root 的调度模式

    Returns:
        "sync" - 同步渲染
        "concurrent" - 并发渲染
        "idle" - 空闲时渲染
    """
    lanes = getattr(root, "pending_lanes", NoLanes)

    if lanes & IdleLane:
        return "idle"

    if includesSyncLane(lanes) or includesBlockingLane(lanes):
        return "sync"

    if includesExpiredLane(lanes):
        return "sync"

    return "concurrent"


def shouldScheduleIdleWork(root: object) -> bool:
    """检查是否应该调度空闲工作"""
    pendingLanes = getattr(root, "pending_lanes", NoLanes)
    return (pendingLanes & IdleLane) != NoLanes


# =============================================================================
# ensureRootIsScheduled - 核心调度入口
# =============================================================================


def ensureRootIsScheduled(root: object) -> None:
    """
    确保 Root 被调度

    核心调度逻辑：
    1. 检查是否需要中断当前渲染（抢占）
    2. 将 Root 加入调度队列
    3. 触发微任务调度

    Args:
        root: Fiber Root
    """
    global firstScheduledRoot, lastScheduledRoot

    pendingLanes = getattr(root, "pending_lanes", NoLanes)

    if pendingLanes == NoLanes:
        # 没有待处理的工作
        return

    # 获取最高优先级
    priority = getHighestPriorityLane(pendingLanes)

    # 检查是否需要中断当前渲染（抢占式更新）
    if _shouldInterruptCurrentRender(root, priority):
        _interruptCurrentRender(root)

    # 更新 Root 的调度优先级
    root.callback_priority = priority
    root.scheduled_callback_priority = priority

    # 加入调度队列（链表）
    if firstScheduledRoot is None:
        # 队列为空，作为第一个元素
        firstScheduledRoot = lastScheduledRoot = root
        root.next = None
    elif root is not firstScheduledRoot and getattr(root, "next", None) is None:
        # Root 不在队列中，添加到队尾
        lastScheduledRoot.next = root
        lastScheduledRoot = root
        root.next = None

    # 触发微任务调度
    ensureScheduleIsScheduled()


def _shouldInterruptCurrentRender(root: object, nextLane: int) -> bool:
    """
    检查是否应该中断当前渲染

    当新的 lane 优先级高于当前渲染的 lane 时，需要中断
    """
    global currentlyRenderingRoot, currentlyRenderingLane

    if currentlyRenderingRoot is not root:
        return False

    if currentlyRenderingLane == NoLane:
        return False

    # 数值越小优先级越高
    return nextLane < currentlyRenderingLane and nextLane != NoLane


def _interruptCurrentRender(root: object) -> None:
    """中断当前渲染"""
    # 标记当前渲染为可中断
    if hasattr(root, "work_in_progress"):
        wip = root.work_in_progress
        if wip is not None:
            # 保存当前进度
            root.saved_work_in_progress = wip
            root.saved_lanes = getattr(root, "work_in_progress_lanes", NoLanes)


# =============================================================================
# flushSyncWorkOnAllRoots - 刷新同步工作
# =============================================================================


def flushSyncWorkOnAllRoots() -> None:
    """
    刷新所有 Root 上的同步工作

    用于调试和测试场景
    """
    global firstScheduledRoot, lastScheduledRoot

    root = firstScheduledRoot
    previous = None

    while root is not None:
        next_root = getattr(root, "next", None)

        if includesSyncLane(getattr(root, "pending_lanes", NoLanes)):
            # 同步优先级，立即执行
            if hasattr(root, "_reconciler"):
                root._reconciler.flush_sync_work(root)

            # 清除调度状态
            root.callback_priority = NoLane
            root.scheduled_callback_priority = NoLane

            # 从队列中移除
            if previous is None:
                firstScheduledRoot = next_root
            else:
                previous.next = next_root

            if root is lastScheduledRoot:
                lastScheduledRoot = previous

            root.next = None
        else:
            # 更新优先级
            root.callback_priority = getHighestPriorityLane(getattr(root, "pending_lanes", NoLanes))
            root.scheduled_callback_priority = root.callback_priority
            previous = root

        root = next_root


# =============================================================================
# scheduleTaskForRootDuringMicrotask - 微任务调度
# =============================================================================


def scheduleTaskForRootDuringMicrotask(root: object) -> dict | None:
    """
    在微任务期间为 Root 调度任务

    Returns:
        任务配置字典，如果不需要调度则返回 None
    """
    pendingLanes = getattr(root, "pending_lanes", NoLanes)

    if pendingLanes == NoLanes:
        return None

    priority = getHighestPriorityLane(pendingLanes)
    mode = getRootScheduleMode(root)

    return {
        "root": root,
        "next_lanes": priority,
        "callback_priority": priority,
        "mode": mode,
    }


# =============================================================================
# processRootScheduleInMicrotask - 微任务处理
# =============================================================================


def processRootScheduleInMicrotask() -> None:
    """
    在微任务中处理所有待调度的 Root

    这是 React 调度器的核心：
    1. 遍历所有待调度的 Root
    2. 根据优先级选择渲染模式
    3. 执行渲染工作
    """
    global didScheduleMicrotask, firstScheduledRoot, lastScheduledRoot, isExecutingMicrotask

    didScheduleMicrotask = False
    isExecutingMicrotask = True

    try:
        root = firstScheduledRoot

        while root is not None:
            next_root = getattr(root, "next", None)
            task = scheduleTaskForRootDuringMicrotask(root)

            if task is not None:
                mode = task["mode"]
                pendingLanes = getattr(root, "pending_lanes", NoLanes)
                lanes = getHighestPriorityLane(pendingLanes)

                if mode == "sync":
                    # 同步渲染
                    if hasattr(root, "_reconciler"):
                        root._reconciler.flush_sync_work(root)

                    # 清除调度状态
                    root.callback_priority = NoLane
                    root.scheduled_callback_priority = NoLane
                    root.next = None
                else:
                    # 并发渲染 - 使用 performWorkOnRoot
                    if hasattr(root, "_reconciler"):
                        from .ReactFiberWorkLoop import performWorkOnRoot
                        performWorkOnRoot(root, lanes, force_sync=False)
            else:
                # 清除调度状态
                root.callback_priority = NoLane
                root.scheduled_callback_priority = NoLane
                root.next = None

            root = next_root

        # 重置调度队列
        firstScheduledRoot = None
        lastScheduledRoot = None
    finally:
        isExecutingMicrotask = False


# =============================================================================
# Scheduler 优先级转换
# =============================================================================


def getCurrentSchedulerPriorityForLanes(lanes: int) -> int:
    """
    获取当前 Lanes 对应的 Scheduler 优先级

    Returns:
        Scheduler 优先级值 (0-4, 越小优先级越高)
    """
    if lanes == NoLanes:
        from .ReactEventPriorities import NormalSchedulerPriority
        return NormalSchedulerPriority

    # 转换为事件优先级
    from .ReactEventPriorities import lanesToEventPriority
    event_priority = lanesToEventPriority(lanes)

    # 转换为 Scheduler 优先级
    return eventPriorityToSchedulerPriority(event_priority)


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    # 全局状态
    "firstScheduledRoot",
    "lastScheduledRoot",
    "didScheduleMicrotask",
    "currentlyRenderingRoot",
    "currentlyRenderingLane",
    "isExecutingMicrotask",
    # 核心函数
    "getNextLanes",
    "getEntangledLanes",
    "shouldTimeSlice",
    "ensureRootIsScheduled",
    # 调度队列
    "scheduleImmediateRootScheduleTask",
    "ensureScheduleIsScheduled",
    "resetRootSchedule",
    # 调度模式
    "getRootLaneFamily",
    "getRootScheduleMode",
    "shouldScheduleIdleWork",
    # 刷新同步工作
    "flushSyncWorkOnAllRoots",
    # 微任务处理
    "scheduleTaskForRootDuringMicrotask",
    "processRootScheduleInMicrotask",
    # Scheduler 优先级
    "getCurrentSchedulerPriorityForLanes",
]
