"""
React Fiber Error Logger - 错误日志记录

用于记录捕获的错误和未捕获的错误。
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .ReactCapturedValue import CapturedValue

# 配置日志记录
_logger = logging.getLogger("react.reconciler.error")


def log_uncaught_error(root: Any, error_info: CapturedValue) -> None:
    """
    记录未捕获的错误

    在 Root 级别捕获的错误，通常是致命错误。

    Args:
        root: FiberRoot 节点
        error_info: 捕获的错误信息
    """
    error = error_info.value
    stack = error_info.stack
    source = error_info.source

    message = _format_error_message("Uncaught error", error, stack, source)
    _logger.error(message)

    # 在开发环境中，打印更详细的信息
    _log_dev_details(error, source)


def log_caught_error(root: Any, fiber: Any, error_info: CapturedValue) -> None:
    """
    记录被错误边界捕获的错误

    Args:
        root: FiberRoot 节点
        fiber: 捕获错误的 Fiber 节点（错误边界）
        error_info: 捕获的错误信息
    """
    error = error_info.value
    stack = error_info.stack
    source = error_info.source

    boundary_name = _get_component_name(fiber)
    source_name = _get_component_name(source)

    message = _format_error_message(
        f"Error caught by '{boundary_name}'", error, stack, source, source_name
    )
    _logger.error(message)

    # 在开发环境中，打印更详细的信息
    _log_dev_details(error, source, boundary_name)


def _format_error_message(
    prefix: str,
    error: Any,
    stack: Optional[str],
    source: Optional[Any],
    source_name: Optional[str] = None,
) -> str:
    """
    格式化错误消息

    Args:
        prefix: 消息前缀
        error: 错误对象
        stack: 堆栈信息
        source: 源 Fiber
        source_name: 源组件名称

    Returns:
        格式化的错误消息字符串
    """
    parts = [prefix]

    # 错误类型和消息
    error_str = str(error)
    if error_str:
        parts.append(f": {error_str}")

    # 源组件
    if source_name is None and source is not None:
        source_name = _get_component_name(source)

    if source_name:
        parts.append(f"\n  in {source_name}")

    # 堆栈信息
    if stack:
        parts.append(f"\n  {stack}")

    return "".join(parts)


def _get_component_name(fiber: Optional[Any]) -> Optional[str]:
    """获取 Fiber 对应的组件名称"""
    if fiber is None:
        return None

    # 从 type 获取
    fiber_type = getattr(fiber, "type", None)
    if fiber_type is not None:
        if isinstance(fiber_type, type):
            return getattr(fiber_type, "__name__", None)
        elif callable(fiber_type):
            return getattr(fiber_type, "__name__", None)
        return str(fiber_type)

    # 从 tag 获取
    from .ReactWorkTags import getWorkTagName

    tag = getattr(fiber, "tag", None)
    if tag is not None:
        return getWorkTagName(tag)

    return None


def _log_dev_details(error: Any, source: Optional[Any], boundary_name: Optional[str] = None) -> None:
    """
    在开发环境中记录详细的错误信息

    Args:
        error: 错误对象
        source: 源 Fiber
        boundary_name: 错误边界名称
    """
    # 获取组件堆栈
    if source is not None:
        component_stack = _get_component_stack(source)
        if component_stack:
            _logger.debug(f"Component stack:\n{component_stack}")


def _get_component_stack(fiber: Any) -> str:
    """
    获取组件堆栈字符串

    Args:
        fiber: Fiber 节点

    Returns:
        组件堆栈字符串
    """
    stack_parts = []
    current = fiber

    while current is not None:
        name = _get_component_name(current)
        if name:
            stack_parts.append(f"    in {name}")
        current = getattr(current, "return_fiber", getattr(current, "return", None))

    return "\n".join(stack_parts) if stack_parts else ""


def log_hydration_error(error: Any, source: Optional[Any] = None) -> None:
    """
    记录水合错误

    Args:
        error: 错误对象
        source: 源 Fiber（可选）
    """
    message = f"Hydration error: {error}"
    if source is not None:
        name = _get_component_name(source)
        if name:
            message += f"\n  in {name}"

    _logger.error(message)


def recoverable_error(message: str) -> Exception:
    """
    创建可恢复错误异常

    Args:
        message: 错误消息

    Returns:
        Exception 对象
    """
    return Exception(f"[Recoverable] {message}")


# =============================================================================
# 开发工具
# =============================================================================


def set_error_handler(handler: Optional[callable]) -> None:
    """
    设置自定义错误处理器

    Args:
        handler: 错误处理函数
    """
    global _custom_error_handler
    _custom_error_handler = handler


_custom_error_handler: Optional[callable] = None


__all__ = [
    "log_uncaught_error",
    "log_caught_error",
    "log_hydration_error",
    "recoverable_error",
    "set_error_handler",
]
