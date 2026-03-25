"""
React Fiber Concurrent Updates - 并发更新队列

实现并发渲染时的更新队列管理，支持在渲染过程中接收更新并延迟处理。
这是 React 18 并发模式的核心实现之一。
"""

from __future__ import annotations

from typing import Any, Optional

from .ReactFiberLane import NoLane, NoLanes, mergeLanes
from .ReactFiberFlags import NoFlags
from .ReactWorkTags import HostRoot, OffscreenComponent


# =============================================================================
# 并发更新数据结构
# =============================================================================


class ConcurrentUpdate:
    """
    并发更新节点

    使用循环链表存储更新，与 React JS 版本保持一致。
    """

    __slots__ = ("next", "lane", "payload", "callback")

    def __init__(self, lane: int = NoLane, payload: Any = None, callback: Any = None) -> None:
        self.next: Optional[ConcurrentUpdate] = None  # 指向下一个更新
        self.lane: int = lane  # 更新的 lane 优先级
        self.payload: Any = payload  # 更新的数据
        self.callback: Any = callback  # 更新完成后的回调


class ConcurrentQueue:
    """
    并发更新队列

    使用循环链表实现，pending 指向最后一个节点以实现 O(1) 插入。
    """

    __slots__ = ("pending",)

    def __init__(self) -> None:
        self.pending: Optional[ConcurrentUpdate] = None  # 指向队列最后一个节点


# =============================================================================
# 全局并发队列存储
# =============================================================================

# 存储并发期间的更新：[fiber, queue, update, lane, ...]
# 使用数组而非字典是为了避免在并发渲染时创建过多对象
_concurrent_que: list[Any] = []
_concurrent_que_index: int = 0

# 记录并发期间更新的所有 lanes
_concurrently_updated_lanes: int = NoLanes


# =============================================================================
# 核心 enqueue 函数
# =============================================================================


def _enqueue_update(
    fiber: Any,
    queue: Optional[ConcurrentQueue],
    update: Optional[ConcurrentUpdate],
    lane: int,
) -> None:
    """
    将更新添加到并发队列中

    在并发渲染期间，更新不会立即应用到 Fiber，而是存储在并发队列中，
    等待当前渲染完成后再处理。

    Args:
        fiber: 目标 Fiber 节点
        queue: Hook 或 Class 组件的更新队列
        update: 更新对象
        lane: 更新优先级
    """
    global _concurrent_que_index, _concurrently_updated_lanes

    # 将更新信息存储到全局数组中
    _concurrent_que.append(fiber)
    _concurrent_que.append(queue)
    _concurrent_que.append(update)
    _concurrent_que.append(lane)
    _concurrent_que_index += 4

    # 记录更新的 lane
    _concurrently_updated_lanes = mergeLanes(_concurrently_updated_lanes, lane)

    # 立即更新 fiber 的 lane 字段，用于 bailout 检查
    fiber.lanes = mergeLanes(getattr(fiber, "lanes", NoLanes), lane)

    # 同时更新 alternate fiber
    alternate = getattr(fiber, "alternate", None)
    if alternate is not None:
        alternate.lanes = mergeLanes(getattr(alternate, "lanes", NoLanes), lane)


# =============================================================================
# 公开 API - Hook 更新
# =============================================================================


def enqueue_concurrent_hook_update(
    fiber: Any,
    queue: Any,
    update: Any,
    lane: int,
) -> Optional[Any]:
    """
    将 Hook 更新添加到并发队列

    用于 useState、useReducer 等 Hook 的并发更新。

    Args:
        fiber: 目标 Fiber 节点
        queue: Hook 的更新队列
        update: Hook 更新对象
        lane: 更新优先级

    Returns:
        FiberRoot 或 None
    """
    concurrent_queue: Optional[ConcurrentQueue] = queue if queue is not None else None
    concurrent_update: Optional[ConcurrentUpdate] = update if update is not None else None

    _enqueue_update(fiber, concurrent_queue, concurrent_update, lane)

    return _get_root_for_updated_fiber(fiber)


def enqueue_concurrent_hook_update_and_eagerly_bailout(
    fiber: Any,
    queue: Any,
    update: Any,
) -> None:
    """
    将 Hook 更新添加到并发队列并立即 bailout

    用于不需要触发重渲染的更新（如 setState 到相同值）。
    更新仍会被队列保存，以防后续有更高优先级的更新导致 rebasing。

    Args:
        fiber: 目标 Fiber 节点
        queue: Hook 的更新队列
        update: Hook 更新对象
    """
    # 使用 NoLane 表示不需要触发重渲染
    lane = NoLane

    concurrent_queue: Optional[ConcurrentQueue] = queue if queue is not None else None
    concurrent_update: Optional[ConcurrentUpdate] = update if update is not None else None

    _enqueue_update(fiber, concurrent_queue, concurrent_update, lane)

    # 如果当前不在渲染中，立即处理队列以防内存泄漏
    from .ReactFiberWorkLoop import get_work_in_progress_root

    if get_work_in_progress_root() is None:
        finish_queueing_concurrent_updates()


# =============================================================================
# 公开 API - Class 组件更新
# =============================================================================


def enqueue_concurrent_class_update(
    fiber: Any,
    queue: Any,
    update: Any,
    lane: int,
) -> Optional[Any]:
    """
    将 Class 组件更新添加到并发队列

    Args:
        fiber: 目标 Fiber 节点
        queue: Class 组件的更新队列
        update: Class 组件更新对象
        lane: 更新优先级

    Returns:
        FiberRoot 或 None
    """
    concurrent_queue: Optional[ConcurrentQueue] = queue if queue is not None else None
    concurrent_update: Optional[ConcurrentUpdate] = update if update is not None else None

    _enqueue_update(fiber, concurrent_queue, concurrent_update, lane)

    return _get_root_for_updated_fiber(fiber)


# =============================================================================
# 公开 API - 通用并发渲染
# =============================================================================


def enqueue_concurrent_render_for_lane(
    fiber: Any,
    lane: int,
) -> Optional[Any]:
    """
    为指定 lane 调度并发渲染

    这是最通用的并发更新入口，用于不涉及具体 queue 的更新。

    Args:
        fiber: 目标 Fiber 节点
        lane: 更新优先级

    Returns:
        FiberRoot 或 None
    """
    _enqueue_update(fiber, None, None, lane)
    return _get_root_for_updated_fiber(fiber)


# =============================================================================
# 完成并发更新队列处理
# =============================================================================


def finish_queueing_concurrent_updates() -> None:
    """
    完成并发更新队列的处理

    在并发渲染完成后调用，将所有存储的更新应用到对应的 Fiber 上。
    这个过程会将更新从临时队列转移到实际的 Fiber 队列中。
    """
    global _concurrent_que_index, _concurrently_updated_lanes, _concurrent_que

    end_index = _concurrent_que_index
    _concurrent_que_index = 0
    _concurrently_updated_lanes = NoLanes

    i = 0
    while i < end_index:
        fiber = _concurrent_que[i]
        _concurrent_que[i] = None
        i += 1

        queue: Optional[ConcurrentQueue] = _concurrent_que[i]
        _concurrent_que[i] = None
        i += 1

        update: Optional[ConcurrentUpdate] = _concurrent_que[i]
        _concurrent_que[i] = None
        i += 1

        lane: int = _concurrent_que[i]
        _concurrent_que[i] = None
        i += 1

        if queue is not None and update is not None:
            # 将更新添加到队列中（循环链表）
            pending = queue.pending
            if pending is None:
                # 队列为空，创建自循环
                update.next = update
            else:
                # 插入到循环链表末尾
                update.next = pending.next
                pending.next = update
            queue.pending = update

        if lane != NoLane:
            _mark_update_lane_from_fiber_to_root(fiber, update, lane)

    # 清空数组引用，帮助 GC
    _concurrent_que.clear()


# =============================================================================
# 辅助函数
# =============================================================================


def get_concurrently_updated_lanes() -> int:
    """
    获取并发期间更新的所有 lanes

    Returns:
        合并后的 lanes
    """
    return _concurrently_updated_lanes


def _get_root_for_updated_fiber(fiber: Any) -> Optional[Any]:
    """
    从 Fiber 向上遍历找到对应的 Root

    Args:
        fiber: 起始 Fiber 节点

    Returns:
        FiberRoot 或 None
    """
    node = fiber
    while node is not None:
        # 检查是否是 HostRoot
        tag = getattr(node, "tag", None)
        if tag == HostRoot:
            return node

        # 检查是否有 state_node（可能是 FiberRoot）
        state_node = getattr(node, "state_node", None)
        if state_node is not None and hasattr(state_node, "current"):
            return state_node

        # 向上遍历
        parent = getattr(node, "return_fiber", None)
        if parent is None:
            # 没有 parent，检查当前节点是否是 root
            if hasattr(node, "container"):
                return node
            break
        node = parent

    return None


def _mark_update_lane_from_fiber_to_root(
    source_fiber: Any,
    update: Optional[ConcurrentUpdate],
    lane: int,
) -> Optional[Any]:
    """
    从 Fiber 向上标记到 Root 的 lane 路径

    更新 path 上所有节点的 child_lanes，确保更新能够传播到 Root。

    Args:
        source_fiber: 起始 Fiber 节点
        update: 更新对象（可选）
        lane: 更新优先级
    """
    # 更新 source fiber 的 lanes
    source_fiber.lanes = mergeLanes(getattr(source_fiber, "lanes", NoLanes), lane)

    alternate = getattr(source_fiber, "alternate", None)
    if alternate is not None:
        alternate.lanes = mergeLanes(getattr(alternate, "lanes", NoLanes), lane)

    # 向上遍历到 root
    node = source_fiber
    while node is not None:
        # 更新 child_lanes
        node.child_lanes = mergeLanes(getattr(node, "child_lanes", NoLanes), lane)

        alternate = getattr(node, "alternate", None)
        if alternate is not None:
            alternate.child_lanes = mergeLanes(getattr(alternate, "child_lanes", NoLanes), lane)

        # 检查是否是 HostRoot
        tag = getattr(node, "tag", None)
        if tag == HostRoot or getattr(node, "pending_lanes", None) is not None:
            # 更新 root 的 pending_lanes
            node.pending_lanes = mergeLanes(getattr(node, "pending_lanes", NoLanes), lane)
            return node

        # 向上遍历
        parent = getattr(node, "return_fiber", None)
        if parent is None:
            # 没有 parent，检查是否有 container
            container = getattr(node, "container", None)
            if container is not None:
                container.pending_lanes = mergeLanes(
                    getattr(container, "pending_lanes", NoLanes), lane
                )
                return container
            break
        node = parent

    return None

def unsafe_mark_update_lane_from_fiber_to_root(
    source_fiber: Any,
    lane: int,
) -> Optional[Any]:
    """
    不安全地标记更新 lane（用于向后兼容）

    这个方法绕过了正常的并发队列处理，应该只在特殊情况下使用。

    Args:
        source_fiber: 起始 Fiber 节点
        lane: 更新优先级

    Returns:
        FiberRoot 或 None
    """
    root = _get_root_for_updated_fiber(source_fiber)
    _mark_update_lane_from_fiber_to_root(source_fiber, None, lane)
    return root


# =============================================================================
# 调试和开发工具
# =============================================================================


def get_concurrent_queue_size() -> int:
    """
    获取当前并发队列中的更新数量（用于调试）

    Returns:
        队列中的更新数量
    """
    return _concurrent_que_index // 4


def reset_concurrent_queue() -> None:
    """
    重置并发队列（用于调试和测试）
    """
    global _concurrent_que_index, _concurrently_updated_lanes, _concurrent_que
    _concurrent_que_index = 0
    _concurrently_updated_lanes = NoLanes
    _concurrent_que.clear()


# =============================================================================
# 导出
# =============================================================================


__all__ = [
    # 类
    "ConcurrentUpdate",
    "ConcurrentQueue",
    # 核心 API
    "enqueue_concurrent_hook_update",
    "enqueue_concurrent_hook_update_and_eagerly_bailout",
    "enqueue_concurrent_class_update",
    "enqueue_concurrent_render_for_lane",
    # 队列处理
    "finish_queueing_concurrent_updates",
    "get_concurrently_updated_lanes",
    # 辅助函数
    "_get_root_for_updated_fiber",
    "_mark_update_lane_from_fiber_to_root",
    "unsafe_mark_update_lane_from_fiber_to_root",
    # 调试工具
    "get_concurrent_queue_size",
    "reset_concurrent_queue",
    # 兼容性别名（驼峰命名）
    "markUpdateLaneFromFiberToRoot",
]

# =============================================================================
# 兼容性别名（驼峰命名，用于向后兼容）
# =============================================================================

# 驼峰命名别名，用于与旧代码和测试兼容
markUpdateLaneFromFiberToRoot = _mark_update_lane_from_fiber_to_root
