"""
React Captured Value - 捕获的值包装

用于在错误边界和 Suspense 中包装捕获的错误或 wakeable 值。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, TypeVar

T = TypeVar("T")


@dataclass
class CapturedValue:
    """
    捕获的值包装

    包装错误值或其他异常值，并附带源 Fiber 和堆栈信息。
    用于错误边界和 Suspense 的错误传播。

    Attributes:
        value: 捕获的值（错误对象、wakeable 等）
        source: 抛出错误的源 Fiber 节点
        stack: 堆栈跟踪信息
    """

    value: Any
    source: Optional[Any] = None  # Fiber 节点
    stack: Optional[str] = None


# 用于跟踪已包装的错误值，避免重复创建
_captured_stacks: dict[int, CapturedValue] = {}


def create_captured_value_at_fiber(value: Any, source: Any) -> CapturedValue:
    """
    在 Fiber 处创建捕获的值

    如果值已经是一个错误对象，调用此函数以获取准确的堆栈信息。

    Args:
        value: 要捕获的值
        source: 源 Fiber 节点

    Returns:
        CapturedValue 包装对象
    """
    # 如果值是对象，检查是否已经包装过
    if isinstance(value, dict) or hasattr(value, "__dict__"):
        value_id = id(value)
        if value_id in _captured_stacks:
            return _captured_stacks[value_id]

    # 获取堆栈信息
    stack = get_stack_by_fiber_in_dev_and_prod(source)

    captured = CapturedValue(value=value, source=source, stack=stack)

    # 缓存已包装的值
    if isinstance(value, dict) or hasattr(value, "__dict__"):
        _captured_stacks[value_id] = captured

    return captured


def create_captured_value_from_error(value: Exception, stack: Optional[str]) -> CapturedValue:
    """
    从错误对象创建捕获的值

    Args:
        value: 错误对象
        stack: 堆栈信息

    Returns:
        CapturedValue 包装对象
    """
    captured = CapturedValue(value=value, source=None, stack=stack)
    if stack is not None:
        _captured_stacks[id(value)] = captured
    return captured


def get_stack_by_fiber_in_dev_and_prod(source: Any) -> Optional[str]:
    """
    获取 Fiber 的堆栈信息

    在开发和生产环境中都返回堆栈信息。

    Args:
        source: Fiber 节点

    Returns:
        堆栈字符串或 None
    """
    # 简化实现：返回 Fiber 的基本信息
    # 在完整版中，应该生成组件树的路径
    fiber_name = _get_fiber_name(source)
    if fiber_name:
        return f"in {fiber_name}"
    return None


def _get_fiber_name(fiber: Any) -> Optional[str]:
    """获取 Fiber 节点的名称"""
    if fiber is None:
        return None

    # 尝试从 type 获取名称
    fiber_type = getattr(fiber, "type", None)
    if fiber_type is not None:
        if isinstance(fiber_type, type):
            return getattr(fiber_type, "__name__", str(fiber_type))
        elif callable(fiber_type):
            return getattr(fiber_type, "__name__", str(fiber_type))
        else:
            return str(fiber_type)

    # 从 tag 获取名称
    from .ReactWorkTags import getWorkTagName

    tag = getattr(fiber, "tag", None)
    if tag is not None:
        tag_name = getWorkTagName(tag)
        if tag_name:
            return tag_name

    return None


def clear_captured_stacks() -> None:
    """
    清空捕获的堆栈缓存

    用于测试和内存管理。
    """
    global _captured_stacks
    _captured_stacks.clear()


__all__ = [
    "CapturedValue",
    "create_captured_value_at_fiber",
    "create_captured_value_from_error",
    "get_stack_by_fiber_in_dev_and_prod",
    "clear_captured_stacks",
]
