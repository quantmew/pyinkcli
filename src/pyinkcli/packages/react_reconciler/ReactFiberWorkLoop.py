"""
React Fiber Work Loop - 可中断的工作循环实现

实现基于时间切片和生成器的可中断渲染，支持抢占式更新。
"""

from __future__ import annotations

import asyncio
import time
from types import GeneratorType
from typing import Any, Generator, Optional

from .ReactEventPriorities import (
    DefaultEventPriority,
    DiscreteEventPriority,
    TransitionEventPriority,
)
from .ReactFiberBeginWork import begin_work, reset_did_receive_update
from .ReactFiberCommitWork import CommitList, PreparedCommit, commit_root, prepare_passive_effects, run_prepared_commit_effects
from .ReactFiberCompleteWork import complete_work, complete_tree
from .ReactFiberConcurrentUpdates import (
    finish_queueing_concurrent_updates,
    get_concurrently_updated_lanes,
)
from .ReactFiberLane import (
    DefaultLane,
    IdleLane,
    NoLane,
    NoLanes,
    SyncLane,
    TransitionLanes,
    getHighestPriorityLane,
    includesBlockingLane,
    includesExpiredLane,
    laneToMask,
    mergeLanes,
    removeLanes,
)
from .ReactSharedInternals import shared_internals

# =============================================================================
# 全局状态
# =============================================================================

_work_in_progress_root: Optional[Any] = None
_work_in_progress_root_render_lanes: int = 0
_root_with_pending_passive_effects: Optional[Any] = None
_pending_passive_effect_lanes: int = 0
_has_pending_commit_effects: bool = False

# 时间切片配置
_yield_interval = 50  # 每 50 个节点让出一次
_time_slice_ms = 4  # 4ms 时间切片（与 React 默认值对齐）

# 工作循环状态
_is_work_loop_suspended = False
_last_yield_time = 0


# =============================================================================
# ShouldYield 时间切片支持
# =============================================================================


def shouldYield() -> bool:
    """
    检查是否应该让出主线程控制权

    基于时间切片：如果距离上次让出超过 _time_slice_ms，则让出
    """
    global _last_yield_time
    current_time = time.perf_counter() * 1000  # 转换为毫秒

    if current_time - _last_yield_time >= _time_slice_ms:
        return True
    return False


def forceYield() -> None:
    """强制让出控制权"""
    global _last_yield_time
    _last_yield_time = time.perf_counter() * 1000


def markYield() -> None:
    """标记已让出，重置时间"""
    global _last_yield_time
    _last_yield_time = time.perf_counter() * 1000


# =============================================================================
# 工作循环配置
# =============================================================================


def get_work_in_progress_root() -> Optional[Any]:
    """
    获取当前正在工作的 root

    Returns:
        当前的 FiberRoot 或 None
    """
    return _work_in_progress_root


def shouldTimeSlice(root: Any, lanes: int) -> bool:
    """
    判断是否应该使用时间切片

    当不包含阻塞性 lane 且没有过期 lane 时，使用并发渲染
    """
    return (
        not includesBlockingLane(lanes)
        and not includesExpiredLane(lanes)
        and not checkIfRootIsPrerendering(root, lanes)
    )


def checkIfRootIsPrerendering(root: Any, lanes: int) -> bool:
    """
    检查 root 是否处于预渲染模式
    简化实现：默认返回 False
    """
    return getattr(root, "is_prerendering", False)


def hasHigherPriorityWork(root: Any, current_lanes: int) -> bool:
    """
    检查是否有更高优先级的工作需要处理
    """
    pending_lanes = getattr(root, "pending_lanes", NoLanes)
    if pending_lanes == NoLanes:
        return False

    # 获取最高优先级的 pending lane
    next_lane = getHighestPriorityLane(pending_lanes)
    current_lane = getHighestPriorityLane(current_lanes)

    # 数值越小优先级越高
    return next_lane < current_lane and next_lane != NoLane


def requestUpdateLane() -> int:
    current_transition = getattr(shared_internals, "current_transition", None)
    if current_transition is not None:
        return TransitionEventPriority
    current_priority = getattr(shared_internals, "current_update_priority", NoLane)
    if current_priority and current_priority != NoLane:
        return current_priority
    return DefaultEventPriority


# =============================================================================
# 可中断的工作单元
# =============================================================================


class WorkLoopResult:
    """工作循环执行结果"""

    def __init__(self) -> None:
        self.completed: bool = False
        self.yielded: bool = False
        self.preempted: bool = False
        self.error: Optional[Exception] = None
        self.work_in_progress: Optional[Any] = None


def performUnitOfWork(
    fiber: Any, count: int = 0
) -> Generator[dict[str, Any], None, Optional[Any]]:
    """
    执行单个工作单元，支持中断

    使用生成器实现可中断的执行流程
    """
    global _work_in_progress_root

    # 检查是否需要让出（基于节点计数）
    if count > 0 and count % _yield_interval == 0:
        yield {"type": "yield", "reason": "interval", "fiber": fiber, "count": count}
        # 等待恢复
        markYield()

    try:
        # 执行实际的 fiber 工作
        next_fiber = _processFiber(fiber)

        yield {"type": "progress", "fiber": fiber, "next": next_fiber}

        return next_fiber
    except Exception as e:
        yield {"type": "error", "fiber": fiber, "error": e}
        raise


def _processFiber(fiber: Any) -> Optional[Any]:
    """
    处理单个 Fiber 节点

    执行 beginWork 和 completeWork 阶段，返回下一个要处理的 Fiber。
    """
    global _work_in_progress_root_render_lanes

    # 获取 alternate fiber（current）
    current = getattr(fiber, "alternate", None)

    # Begin 阶段：处理 Fiber 并返回第一个子节点
    try:
        child = begin_work(current, fiber, _work_in_progress_root_render_lanes)
        if child is not None:
            return child
    except Exception as e:
        # TODO: 完善的错误边界处理
        raise

    # Complete 阶段：完成 Fiber 并返回 sibling 或父节点的 sibling
    node = fiber
    while node is not None:
        current_node = getattr(node, "alternate", None)
        sibling = getattr(node, "sibling", None)

        # 调用 completeWork
        next_fiber = complete_work(current_node, node, _work_in_progress_root_render_lanes)

        if next_fiber is not None:
            return next_fiber

        # 没有 sibling，返回到父节点
        node = getattr(node, "return_fiber", getattr(node, "return", None))

    return None


async def renderRootConcurrent(
    root: Any, lanes: int
) -> AsyncGenerator[dict[str, Any], None]:
    """
    并发渲染 root，支持时间切片和抢占

    使用 async/await 和生成器实现可中断的渲染流程
    """
    global _work_in_progress_root, _work_in_progress_root_render_lanes, _is_work_loop_suspended, _last_yield_time

    _work_in_progress_root = root
    _work_in_progress_root_render_lanes = lanes
    _is_work_loop_suspended = False
    _last_yield_time = time.perf_counter() * 1000

    # 获取 work-in-progress fiber
    work_in_progress = getattr(root, "work_in_progress", None)
    if work_in_progress is None:
        work_in_progress = getattr(root, "current", None)

    count = 0
    start_time = time.perf_counter()

    try:
        while work_in_progress is not None and not _is_work_loop_suspended:
            # 检查时间切片
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            if elapsed_ms >= _time_slice_ms:
                yield {
                    "type": "time_slice",
                    "work_in_progress": work_in_progress,
                    "elapsed_ms": elapsed_ms,
                }
                # 让出控制权
                await asyncio.sleep(0)
                start_time = time.perf_counter()
                _last_yield_time = time.perf_counter() * 1000

            # 检查抢占
            if hasHigherPriorityWork(root, lanes):
                yield {
                    "type": "preempted",
                    "work_in_progress": work_in_progress,
                    "reason": "higher_priority",
                }
                return

            # 执行工作单元
            work_gen = performUnitOfWork(work_in_progress, count)
            result = None

            for work_result in work_gen:
                if work_result.get("type") == "yield":
                    # 生成器请求让出
                    yield work_result
                    await asyncio.sleep(0)
                    start_time = time.perf_counter()
                elif work_result.get("type") == "progress":
                    work_in_progress = work_result.get("next")
                    count += 1
                    break
                elif work_result.get("type") == "error":
                    raise work_result.get("error")

    finally:
        _work_in_progress_root = None
        _work_in_progress_root_render_lanes = 0


def renderRootSync(root: Any, lanes: int, force_sync: bool = False) -> Optional[PreparedCommit]:
    """
    同步渲染 root，不支持中断

    用于高优先级更新或遗留模式

    Returns:
        PreparedCommit 或 None
    """
    global _work_in_progress_root, _work_in_progress_root_render_lanes

    _work_in_progress_root = root
    _work_in_progress_root_render_lanes = lanes

    work_in_progress = getattr(root, "work_in_progress", None)
    if work_in_progress is None:
        work_in_progress = getattr(root, "current", None)

    prepared_commit: Optional[PreparedCommit] = None

    try:
        # Render 阶段：开始工作循环
        while work_in_progress is not None:
            # 同步执行，不让出控制权
            work_in_progress = _processFiber(work_in_progress)

        # Render 阶段完成，处理并发队列
        finish_queueing_concurrent_updates()

        # Commit 阶段
        prepared_commit = commit_root(root, lanes)

    finally:
        _work_in_progress_root = None
        _work_in_progress_root_render_lanes = 0

    return prepared_commit


# =============================================================================
# 工作循环入口
# =============================================================================


def performWorkOnRoot(root: Any, lanes: int, force_sync: bool = False) -> Optional[PreparedCommit]:
    """
    在 root 上执行工作

    根据情况选择同步或并发渲染

    Returns:
        PreparedCommit 或 None
    """
    selected_lanes = getHighestPriorityLane(lanes) if lanes else lanes
    reconciler = getattr(root, "_reconciler", None)
    container = getattr(root, "container", root)
    if reconciler is not None and hasattr(reconciler, "flush_scheduled_updates"):
        reconciler.flush_scheduled_updates(
            container,
            selected_lanes,
            lanes=selected_lanes,
            consume_all=False,
        )
        return None

    should_time_slice = not force_sync and shouldTimeSlice(root, selected_lanes)

    if should_time_slice:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_runConcurrentWork(root, selected_lanes))
        finally:
            loop.close()
    return renderRootSync(root, selected_lanes, force_sync)


async def _runConcurrentWork(root: Any, lanes: int) -> Optional[PreparedCommit]:
    """运行并发工作的异步包装器"""
    prepared_commit: Optional[PreparedCommit] = None

    async for result in renderRootConcurrent(root, lanes):
        # 处理结果
        if result.get("type") == "error":
            raise result.get("error")

    # 渲染完成后，处理并发队列
    finish_queueing_concurrent_updates()

    # Commit 阶段
    prepared_commit = commit_root(root, lanes)

    return prepared_commit


# =============================================================================
# 工作循环状态访问器
# =============================================================================


def getWorkInProgressRoot() -> Optional[Any]:
    """获取当前正在工作的 root"""
    return _work_in_progress_root


def getWorkInProgressRootRenderLanes() -> int:
    """获取当前正在工作的 root 的渲染 lanes"""
    return _work_in_progress_root_render_lanes


def getRootWithPendingPassiveEffects() -> Optional[Any]:
    """获取有待处理被动效果的 root"""
    return _root_with_pending_passive_effects


def getPendingPassiveEffectsLanes() -> int:
    """获取有待处理被动效果的 lanes"""
    return _pending_passive_effect_lanes


def hasPendingCommitEffects() -> bool:
    """检查是否有待处理的提交效果"""
    return _has_pending_commit_effects


def isWorkLoopSuspendedOnData() -> bool:
    """检查工作循环是否因等待数据而挂起"""
    return _is_work_loop_suspended


# =============================================================================
# 被动效果处理
# =============================================================================


def flushPendingEffects() -> None:
    """
    刷新所有待处理的被动效果

    执行 useEffect 的清理函数和回调函数
    """
    global _root_with_pending_passive_effects, _pending_passive_effect_lanes, _has_pending_commit_effects

    from ...hooks import _runtime as hooks_runtime

    # 执行卸载组件的清理函数
    for fiber in list(
        getattr(hooks_runtime._runtime, "pending_passive_unmount_fibers", [])
    ):
        hook = getattr(fiber, "hook_head", None)
        if hook and callable(getattr(hook, "cleanup", None)):
            hook.cleanup()
    getattr(
        hooks_runtime._runtime, "pending_passive_unmount_fibers", []
    ).clear()

    # 执行挂载组件的效果
    for hook in list(
        getattr(hooks_runtime._runtime, "pending_passive_mount_effects", [])
    ):
        if callable(getattr(hook, "cleanup", None)):
            hook.cleanup()
        hook.cleanup = hook.callback() if callable(hook.callback) else None
        hook.needs_run = False
        hook.queued = False
    getattr(hooks_runtime._runtime, "pending_passive_mount_effects", []).clear()

    # 执行 fibers 中的效果
    for fiber in getattr(hooks_runtime._runtime, "fibers", {}).values():
        queue = getattr(fiber, "update_queue", None)
        effect = getattr(queue, "last_effect", None)
        if effect is not None and callable(effect.create):
            effect.create()

    hooks_runtime._runtime.fibers = {}
    _root_with_pending_passive_effects = None
    _pending_passive_effect_lanes = 0
    _has_pending_commit_effects = False


def schedulePendingEffects(root: Any, lanes: int) -> None:
    """调度被动效果"""
    global _root_with_pending_passive_effects, _pending_passive_effect_lanes
    _root_with_pending_passive_effects = root
    _pending_passive_effect_lanes = lanes


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    # 配置
    "shouldYield",
    "forceYield",
    "markYield",
    "shouldTimeSlice",
    "checkIfRootIsPrerendering",
    "hasHigherPriorityWork",
    "requestUpdateLane",
    # 工作单元
    "performUnitOfWork",
    "WorkLoopResult",
    # 渲染入口
    "renderRootConcurrent",
    "renderRootSync",
    "performWorkOnRoot",
    # 状态访问器
    "getWorkInProgressRoot",
    "getWorkInProgressRootRenderLanes",
    "getRootWithPendingPassiveEffects",
    "getPendingPassiveEffectsLanes",
    "hasPendingCommitEffects",
    "isWorkLoopSuspendedOnData",
    # 被动效果
    "flushPendingEffects",
    "schedulePendingEffects",
    # Lane 函数（从 ReactFiberLane 重新导出）
    "laneToMask",
    "mergeLanes",
    "removeLanes",
    "getHighestPriorityLane",
]
