"""
React Fiber Class Update Queue - 类组件更新队列

实现类组件的更新队列，支持 CaptureUpdate 等更新类型。
"""

from __future__ import annotations

from typing import Any, Optional, Callable

from .ReactFiberLane import Lane, NoLane, mergeLanes


# =============================================================================
# 更新类型标签
# =============================================================================

# 普通状态更新
UpdateState = 0
# 捕获错误的更新（错误边界）
CaptureUpdate = 1
# 强制更新
ForceUpdate = 2
# 替换状态
ReplaceState = 3


# =============================================================================
# Update 数据结构
# =============================================================================


class Update:
    """
    类组件的更新对象

    与 React JS 版本的 update 结构保持一致。
    """

    __slots__ = ("tag", "lane", "next", "payload", "callback")

    def __init__(
        self,
        lane: Lane = NoLane,
        tag: int = UpdateState,
        payload: Any = None,
        callback: Optional[Callable] = None,
    ) -> None:
        self.tag: int = tag  # 更新类型
        self.lane: Lane = lane  # 优先级
        self.next: Optional[Update] = None  # 循环链表指针
        self.payload: Any = payload  # 更新数据（可以是状态对象或返回状态的函数）
        self.callback: Optional[Callable] = callback  # 更新完成后的回调


# =============================================================================
# Update Queue 数据结构
# =============================================================================


class UpdateQueue:
    """
    类组件的更新队列

    使用循环链表实现，pending 指向最后一个节点以实现 O(1) 插入。
    """

    __slots__ = ("pending", "lanes")

    def __init__(self) -> None:
        self.pending: Optional[Update] = None  # 指向队列最后一个节点
        self.lanes: int = NoLanes  # 队列中所有更新的 lanes 合并


# =============================================================================
# Update 创建函数
# =============================================================================


def create_update(lane: Lane) -> Update:
    """
    创建一个更新对象

    Args:
        lane: 更新优先级

    Returns:
        Update 对象
    """
    return Update(lane=lane, tag=UpdateState)


# =============================================================================
# 入队函数
# =============================================================================


def enqueue_update(fiber: Any, update: Update, lane: Lane) -> None:
    """
    将更新添加到队列中

    使用循环链表实现，时间复杂度 O(1)。

    Args:
        fiber: 目标 Fiber 节点
        update: 更新对象
        lane: 更新优先级
    """
    queue = fiber.update_queue

    if queue is None:
        # 创建新队列
        queue = UpdateQueue()
        fiber.update_queue = queue

    # 更新队列的 lanes
    queue.lanes = mergeLanes(queue.lanes, lane)

    # 添加到循环链表
    pending = queue.pending
    if pending is None:
        # 空队列，创建自循环
        update.next = update
    else:
        # 插入到链表末尾
        update.next = pending.next
        pending.next = update

    # 更新 pending 指向新的末尾
    queue.pending = update


def enqueue_captured_update(fiber: Any, update: Update) -> None:
    """
    将捕获的更新（错误边界）添加到队列

    Args:
        fiber: 目标 Fiber 节点
        update: 捕获更新对象
    """
    lane = update.lane
    queue = fiber.update_queue

    if queue is None:
        queue = UpdateQueue()
        fiber.update_queue = queue

    queue.lanes = mergeLanes(queue.lanes, lane)

    pending = queue.pending
    if pending is None:
        update.next = update
    else:
        update.next = pending.next
        pending.next = update

    queue.pending = update


# =============================================================================
# 更新处理函数
# =============================================================================


def process_update_queue(fiber: Any, instance: Any, props: Any, state: Any) -> dict[str, Any]:
    """
    处理更新队列

    按顺序处理所有待处理的更新，计算新的状态。

    Args:
        fiber: Fiber 节点
        instance: 组件实例
        props: 组件 props
        state: 当前状态

    Returns:
        包含新状态的字典
    """
    queue = getattr(fiber, "update_queue", None)

    if queue is None or queue.pending is None:
        return {"state": state, "has_captured_update": False}

    new_state = state
    has_captured_update = False

    # 从循环链表的第一个节点开始处理
    pending = queue.pending
    if pending is not None:
        first = pending.next
        current = first

        while current is not None:
            lane = current.lane

            # 处理不同类型的更新
            tag = current.tag

            if tag == CaptureUpdate:
                has_captured_update = True
                # 错误捕获更新，在 commit 阶段处理

            elif tag == ForceUpdate:
                # 强制更新，不改变状态
                pass

            elif tag == ReplaceState:
                # 替换状态
                payload = current.payload
                if callable(payload):
                    new_state = payload(new_state, props)
                else:
                    new_state = payload

            elif tag == UpdateState:
                # 普通状态更新
                payload = current.payload
                if callable(payload):
                    partial_state = payload(new_state, props)
                    if partial_state is not None:
                        new_state = _merge_state(new_state, partial_state)
                else:
                    if payload is not None:
                        new_state = _merge_state(new_state, payload)

            # 移动到下一个更新
            if current == pending:
                # 已经处理完所有更新
                break
            current = current.next

        # 清空队列
        queue.pending = None
        queue.lanes = NoLane

    return {
        "state": new_state,
        "has_captured_update": has_captured_update,
    }


def _merge_state(current_state: Any, partial_state: Any) -> dict:
    """
    合并部分状态到完整状态

    Args:
        current_state: 当前状态字典
        partial_state: 部分状态字典

    Returns:
        合并后的状态字典
    """
    if current_state is None:
        return dict(partial_state) if isinstance(partial_state, dict) else partial_state

    if isinstance(current_state, dict) and isinstance(partial_state, dict):
        merged = dict(current_state)
        merged.update(partial_state)
        return merged

    # 如果状态不是字典，直接替换
    return partial_state


def clone_update_queue(source: UpdateQueue) -> UpdateQueue:
    """
    克隆更新队列（用于双缓冲）

    Args:
        source: 源队列

    Returns:
        克隆后的队列
    """
    clone = UpdateQueue()
    clone.lanes = source.lanes

    if source.pending is not None:
        # 深拷贝循环链表
        pending = source.pending
        first = pending.next
        current = first
        prev = None

        while current is not None:
            new_update = Update(
                lane=current.lane,
                tag=current.tag,
                payload=current.payload,
                callback=current.callback,
            )

            if prev is None:
                clone.pending = new_update
            else:
                prev.next = new_update

            prev = new_update

            if current == pending:
                # 完成循环
                prev.next = clone.pending
                break
            current = current.next

    return clone


# =============================================================================
# 辅助函数
# =============================================================================


def has_update_queue(fiber: Any) -> bool:
    """检查 Fiber 是否有更新队列"""
    queue = getattr(fiber, "update_queue", None)
    return queue is not None and queue.pending is not None


def get_update_queue_lanes(fiber: Any) -> int:
    """获取更新队列中的所有 lanes"""
    queue = getattr(fiber, "update_queue", None)
    if queue is None:
        return NoLane
    return getattr(queue, "lanes", NoLane)


def clear_update_queue(fiber: Any) -> None:
    """清空更新队列"""
    queue = getattr(fiber, "update_queue", None)
    if queue is not None:
        queue.pending = None
        queue.lanes = NoLane


# =============================================================================
# 错误边界回调处理
# =============================================================================


def call_callback_if_defined(update: Update, context: Any = None) -> None:
    """
    如果更新定义了回调，则执行它

    Args:
        update: 更新对象
        context: 回调执行的上下文（通常是组件实例）
    """
    callback = update.callback
    if callback is not None:
        if context is not None:
            callback(context)
        else:
            callback()


# =============================================================================
# 导出
# =============================================================================


__all__ = [
    # 常量
    "UpdateState",
    "CaptureUpdate",
    "ForceUpdate",
    "ReplaceState",
    # 类
    "Update",
    "UpdateQueue",
    # 创建函数
    "create_update",
    # 入队函数
    "enqueue_update",
    "enqueue_captured_update",
    # 处理函数
    "process_update_queue",
    # 辅助函数
    "has_update_queue",
    "get_update_queue_lanes",
    "clear_update_queue",
    "clone_update_queue",
    "call_callback_if_defined",
    # 兼容性别名
    "UpdateState",
    "CaptureUpdate",
    "ForceUpdate",
    "ReplaceState",
]
