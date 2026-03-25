"""
React Fiber Suspense Context - Suspense 边界上下文管理

管理 Suspense 边界的栈和上下文，用于错误和 suspended 状态的传播。
"""

from __future__ import annotations

from typing import Any, Optional, List


# =============================================================================
# Suspense 边界栈
# =============================================================================

# Suspense 处理器栈
_suspense_handler_stack: List[Any] = []


def push_suspense_handler(handler: Optional[Any]) -> None:
    """
    将 Suspense 处理器推入栈

    Args:
        handler: Suspense 边界 Fiber 或 None
    """
    _suspense_handler_stack.append(handler)


def pop_suspense_handler() -> Optional[Any]:
    """
    从栈中弹出 Suspense 处理器

    Returns:
        被弹出的处理器
    """
    if _suspense_handler_stack:
        return _suspense_handler_stack.pop()
    return None


def get_suspense_handler() -> Optional[Any]:
    """
    获取当前的 Suspense 处理器

    Returns:
        当前栈顶的 Suspense 边界 Fiber 或 None
    """
    if _suspense_handler_stack:
        return _suspense_handler_stack[-1]
    return None


def get_shell_boundary() -> Optional[Any]:
    """
    获取 shell 边界

    Shell 边界是指最外层还未显示 fallback 的 Suspense 边界。

    Returns:
        Shell 边界 Fiber 或 None
    """
    # 简化实现：返回栈底的边界
    if _suspense_handler_stack:
        return _suspense_handler_stack[0]
    return None


# =============================================================================
# Suspense 状态
# =============================================================================

# 记录是否有错误被抛出
_did_render_error: bool = False

# 记录是否 suspend
_did_suspend: bool = False

# 记录是否 suspend 且需要延迟
_did_suspend_delay_if_possible: bool = False


def render_did_error(root: Any = None) -> None:
    """
    记录渲染过程中发生错误

    Args:
        root: FiberRoot（可选）
    """
    global _did_render_error
    _did_render_error = True


def render_did_suspend(root: Any = None) -> None:
    """
    记录渲染过程中发生 suspend

    Args:
        root: FiberRoot（可选）
    """
    global _did_suspend
    _did_suspend = True


def render_did_suspend_delay_if_possible(root: Any = None) -> None:
    """
    记录渲染过程中发生 suspend 且可能需要延迟

    Args:
        root: FiberRoot（可选）
    """
    global _did_suspend_delay_if_possible
    _did_suspend_delay_if_possible = True


def reset_render_error_state() -> None:
    """重置渲染错误状态"""
    global _did_render_error
    _did_render_error = False


def reset_render_suspend_state() -> None:
    """重置渲染 suspend 状态"""
    global _did_suspend, _did_suspend_delay_if_possible
    _did_suspend = False
    _did_suspend_delay_if_possible = False


def get_render_error_state() -> bool:
    """
    获取渲染错误状态

    Returns:
        True 如果渲染过程中发生错误
    """
    return _did_render_error


def get_render_suspend_state() -> bool:
    """
    获取渲染 suspend 状态

    Returns:
        True 如果渲染过程中发生 suspend
    """
    return _did_suspend


# =============================================================================
# 并发错误队列
# =============================================================================

_concurrent_error_queue: List[Any] = []


def queue_concurrent_error(error: Any) -> None:
    """
    将并发错误添加到队列

    Args:
        error: 错误信息（CapturedValue）
    """
    _concurrent_error_queue.append(error)


def get_concurrent_errors() -> List[Any]:
    """
    获取所有并发错误

    Returns:
        错误列表
    """
    return list(_concurrent_error_queue)


def clear_concurrent_errors() -> None:
    """清空并发错误队列"""
    _concurrent_error_queue.clear()


# =============================================================================
# Legacy Error Boundary 跟踪
# =============================================================================

# 记录已经失败的 legacy 错误边界
_failed_legacy_error_boundaries: set = set()


def mark_legacy_error_boundary_as_failed(instance: Any) -> None:
    """
    标记 legacy 错误边界为已失败

    Args:
        instance: 组件实例
    """
    _failed_legacy_error_boundaries.add(id(instance))


def is_already_failed_legacy_error_boundary(instance: Any) -> bool:
    """
    检查 legacy 错误边界是否已失败

    Args:
        instance: 组件实例

    Returns:
        True 如果已失败
    """
    return id(instance) in _failed_legacy_error_boundaries


def clear_failed_legacy_error_boundaries() -> None:
    """清空失败的 legacy 错误边界记录"""
    _failed_legacy_error_boundaries.clear()


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    # Suspense 栈管理
    "push_suspense_handler",
    "pop_suspense_handler",
    "get_suspense_handler",
    "get_shell_boundary",
    # 渲染状态
    "render_did_error",
    "render_did_suspend",
    "render_did_suspend_delay_if_possible",
    "reset_render_error_state",
    "reset_render_suspend_state",
    "get_render_error_state",
    "get_render_suspend_state",
    # 并发错误
    "queue_concurrent_error",
    "get_concurrent_errors",
    "clear_concurrent_errors",
    # Legacy 错误边界
    "mark_legacy_error_boundary_as_failed",
    "is_already_failed_legacy_error_boundary",
    "clear_failed_legacy_error_boundaries",
]
