from __future__ import annotations

_currently_reading_fiber = None


def prepareToReadContext(fiber, render_lanes=None) -> None:
    """
    准备读取 context（兼容旧版本）

    Args:
        fiber: Fiber 节点
        render_lanes: 渲染的 lanes（可选）
    """
    global _currently_reading_fiber
    _currently_reading_fiber = fiber
    fiber.dependencies = []


def finishReadingContext() -> None:
    global _currently_reading_fiber
    _currently_reading_fiber = None


def readContext(context):
    value = getattr(context, "current_value", context.default_value)
    if _currently_reading_fiber is not None:
        _currently_reading_fiber.dependencies.append((context, value))
    return value


def pushProvider(reconciler, context, value) -> None:
    stack = getattr(reconciler, "_context_provider_stack", [])
    stack.append((context, context.current_value))
    reconciler._context_provider_stack = stack
    context.current_value = value


def popProvider(reconciler, context) -> None:
    stack = getattr(reconciler, "_context_provider_stack", [])
    while stack:
        ctx, previous = stack.pop()
        if ctx is context:
            context.current_value = previous
            break
    reconciler._context_provider_stack = stack


def checkIfContextChanged(dependencies) -> bool:
    if not dependencies:
        return False
    return any(getattr(context, "current_value", None) != value for context, value in dependencies)


def prepare_to_read_context(fiber, render_lanes: int) -> None:
    """
    准备读取 context

    Args:
        fiber: Fiber 节点
        render_lanes: 渲染的 lanes
    """
    global _currently_reading_fiber
    _currently_reading_fiber = fiber
    fiber.dependencies = []


def finish_reading_context() -> None:
    """完成读取 context"""
    global _currently_reading_fiber
    _currently_reading_fiber = None


def propagate_context_change(work_in_progress: Any, context: Any, render_lanes: int) -> None:
    """
    传播 context 变化

    Args:
        work_in_progress: 工作中的 Fiber
        context: 变化的 context
        render_lanes: 渲染的 lanes
    """
    # 简化实现：标记需要更新
    from .ReactFiberFlags import Update
    work_in_progress.flags |= getattr(work_in_progress, "flags", 0) | Update


def propagate_parent_context_changes_to_deferred_tree(
    current_source_fiber: Any,
    source_fiber: Any,
    root_render_lanes: int,
) -> None:
    """
    将父节点的 context 变化传播到延迟树

    用于在 suspended 组件重试时，确保 context 变化被正确传播。

    Args:
        current_source_fiber: 当前的源 Fiber
        source_fiber: 工作中的源 Fiber
        root_render_lanes: 渲染的 lanes
    """
    # 简化实现：遍历父节点并传播变化
    # 实际 React 实现更复杂
    pass


# 兼容性别名
finishReadingContext = finish_reading_context
propagateParentContextChangesToDeferredTree = propagate_parent_context_changes_to_deferred_tree

