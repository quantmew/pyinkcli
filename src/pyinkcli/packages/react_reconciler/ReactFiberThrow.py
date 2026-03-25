"""
React Fiber Throw - 异常抛出和错误边界处理

实现错误在 Fiber 树中的传播逻辑，查找并调用错误边界。
"""

from __future__ import annotations

from typing import Any, Optional

from .ReactCapturedValue import CapturedValue, create_captured_value_at_fiber
from .ReactFiberClassUpdateQueue import (
    CaptureUpdate,
    Update,
    create_update,
    enqueue_captured_update,
)
from .ReactFiberFlags import (
    DidCapture,
    ForceClientRender,
    Incomplete,
    NoFlags,
    ShouldCapture,
)
from .ReactFiberLane import (
    NoLane,
    SyncLane,
    mergeLanes,
    pick_arbitrary_lane,
)
from .ReactWorkTags import ClassComponent, HostRoot, OffscreenComponent


# =============================================================================
# 错误更新创建函数
# =============================================================================


def create_root_error_update(
    root: Any,
    error_info: CapturedValue,
    lane: int,
) -> Update:
    """
    创建 Root 错误更新

    用于在 Root 级别捕获错误，卸载整个应用。

    Args:
        root: FiberRoot 节点
        error_info: 捕获的错误信息
        lane: 更新优先级

    Returns:
        Update 对象
    """
    from .ReactFiberErrorLogger import log_uncaught_error

    update = create_update(lane)
    update.tag = CaptureUpdate
    # 通过渲染 null 来卸载 root
    update.payload = {"element": None}

    def callback() -> None:
        log_uncaught_error(root, error_info)

    update.callback = callback
    return update


def create_class_error_update(lane: int) -> Update:
    """
    创建类组件错误更新

    Args:
        lane: 更新优先级

    Returns:
        Update 对象
    """
    update = create_update(lane)
    update.tag = CaptureUpdate
    return update


def initialize_class_error_update(
    update: Update,
    root: Any,
    fiber: Any,
    error_info: CapturedValue,
) -> None:
    """
    初始化类组件错误更新

    设置 getDerivedStateFromError 和 componentDidCatch 回调。

    Args:
        update: 更新对象
        root: FiberRoot 节点
        fiber: 错误边界 Fiber
        error_info: 捕获的错误信息
    """
    from .ReactFiberErrorLogger import log_caught_error, mark_legacy_error_boundary_as_failed

    # 检查是否有 getDerivedStateFromError
    fiber_type = getattr(fiber, "type", None)
    get_derived_state_from_error = None

    if fiber_type is not None:
        get_derived_state_from_error = getattr(
            fiber_type, "getDerivedStateFromError", None
        )

    if callable(get_derived_state_from_error):
        error = error_info.value

        def payload_fn() -> Any:
            return get_derived_state_from_error(error)

        update.payload = payload_fn

        def callback() -> None:
            log_caught_error(root, fiber, error_info)

        update.callback = callback

    # 检查是否有 componentDidCatch
    inst = getattr(fiber, "state_node", None)
    if inst is not None:
        component_did_catch = getattr(inst, "componentDidCatch", None)

        if callable(component_did_catch):
            original_callback = update.callback

            def callback_with_detailed_context() -> None:
                # 调用原始回调（如果有）
                if original_callback is not None:
                    original_callback()

                # 如果不是通过 getDerivedStateFromError 定义的，标记为 legacy
                if get_derived_state_from_error is None:
                    mark_legacy_error_boundary_as_failed(inst)

                # 调用 componentDidCatch
                error = error_info.value
                stack = error_info.stack
                inst.componentDidCatch(
                    error,
                    {"componentStack": stack if stack is not None else ""},
                )

            update.callback = callback_with_detailed_context


# =============================================================================
# 核心 throwException 函数
# =============================================================================


def throw_exception(
    root: Any,
    return_fiber: Optional[Any],
    source_fiber: Any,
    value: Any,
    root_render_lanes: int,
) -> bool:
    """
    抛出异常并通过 Fiber 树向上传播

    查找最近的错误边界或 Suspense 边界来处理异常。

    Args:
        root: FiberRoot 节点
        return_fiber: 父 Fiber
        source_fiber: 抛出异常的源 Fiber
        value: 抛出的值（错误或 wakeable）
        root_render_lanes: 渲染的 lanes

    Returns:
        True 如果发生致命错误（panic），False 否则
    """
    from .ReactFiberErrorLogger import log_caught_error, render_did_error, queue_concurrent_error
    from .ReactFiberSuspenseContext import get_suspense_handler, get_shell_boundary

    # 标记源 Fiber 为 incomplete
    source_fiber.flags |= Incomplete

    # 检查是否是 wakeable（suspended 组件）
    if value is not None and isinstance(value, dict) and "then" in value:
        # 这是一个 wakeable（Promise-like 对象）
        wakeable = value
        reset_suspended_component(source_fiber, root_render_lanes)

        # 查找最近的 Suspense 边界
        suspense_boundary = get_suspense_handler()

        if suspense_boundary is not None:
            suspense_tag = getattr(suspense_boundary, "tag", 0)

            if suspense_tag in (3, 13):  # SuspenseComponent 或 ActivityComponent
                # 清除 ForceClientRender 标志
                suspense_boundary.flags &= ~ForceClientRender

                # 标记 Suspense 边界需要捕获
                mark_suspense_boundary_should_capture(
                    suspense_boundary,
                    return_fiber,
                    source_fiber,
                    root,
                    root_render_lanes,
                )

                # 附加 retry listener
                attach_ping_listener(root, wakeable, root_render_lanes)
                return False

        # 没有找到 Suspense 边界
        # 在并发 root 中，允许无限期挂起
        root_tag = getattr(root, "tag", 0)
        if root_tag == 1:  # ConcurrentRoot
            attach_ping_listener(root, wakeable, root_render_lanes)
            render_did_error(root)
            return False
        else:
            # 在 legacy root 中，这是一个错误
            value = Exception(
                "A component suspended while responding to synchronous input. This "
                "will cause the UI to be replaced with a loading indicator. To "
                "fix, updates that suspend should be wrapped with startTransition."
            )

    # 常规错误处理
    # 向上传播查找错误边界
    error_info = create_captured_value_at_fiber(value, source_fiber)

    if return_fiber is None:
        # 没有返回 Fiber，意味着 root 出错 - 致命错误
        return True

    # 向上遍历查找错误边界
    work_in_progress = return_fiber

    while work_in_progress is not None:
        work_tag = getattr(work_in_progress, "tag", 0)

        if work_tag == HostRoot:
            # 到达 Root，创建 Root 错误更新
            work_in_progress.flags |= ShouldCapture
            lane = pick_arbitrary_lane(root_render_lanes)
            work_in_progress.lanes = mergeLanes(
                getattr(work_in_progress, "lanes", NoLane), lane
            )

            update = create_root_error_update(
                getattr(work_in_progress, "state_node", None),
                error_info,
                lane,
            )
            enqueue_captured_update(work_in_progress, update)
            return False

        elif work_tag == ClassComponent:
            # 检查是否是错误边界
            ctor = getattr(work_in_progress, "type", None)
            instance = getattr(work_in_progress, "state_node", None)

            has_error_boundary = False

            if (getattr(work_in_progress, "flags", 0) & DidCapture) == NoFlags:
                if ctor is not None:
                    has_error_boundary = callable(
                        getattr(ctor, "getDerivedStateFromError", None)
                    )

                if instance is not None:
                    has_error_boundary = has_error_boundary or callable(
                        getattr(instance, "componentDidCatch", None)
                    )

            if has_error_boundary:
                # 标记为需要捕获
                work_in_progress.flags |= ShouldCapture
                lane = pick_arbitrary_lane(root_render_lanes)
                work_in_progress.lanes = mergeLanes(
                    getattr(work_in_progress, "lanes", NoLane), lane
                )

                # 创建并初始化错误更新
                update = create_class_error_update(lane)
                initialize_class_error_update(update, root, work_in_progress, error_info)
                enqueue_captured_update(work_in_progress, update)
                return False

        elif work_tag == OffscreenComponent:
            # 检查是否在隐藏的 Offscreen 中
            memoized_state = getattr(work_in_progress, "memoized_state", None)
            if memoized_state is not None:
                mode = getattr(memoized_state, "mode", None)
                if mode == "hidden":
                    # 在隐藏的 Offscreen 中的错误，标记为需要捕获
                    work_in_progress.flags |= ShouldCapture
                    return False

        # 继续向上遍历
        work_in_progress = getattr(work_in_progress, "return_fiber", None)

    # 没有找到错误边界
    return False


# =============================================================================
# 辅助函数
# =============================================================================


def reset_suspended_component(source_fiber: Any, root_render_lanes: int) -> None:
    """
    重置被挂起的组件

    恢复 memoizedState 到之前的状态，以便重试时可以正确渲染。

    Args:
        source_fiber: 源 Fiber
        root_render_lanes: 渲染的 lanes
    """
    current_source_fiber = getattr(source_fiber, "alternate", None)

    if current_source_fiber is not None:
        # 传播上下文变化到延迟树
        from .ReactFiberNewContext import propagate_parent_context_changes_to_deferred_tree

        propagate_parent_context_changes_to_deferred_tree(
            current_source_fiber,
            source_fiber,
            root_render_lanes,
        )

    # 重置 memoized_state
    tag = getattr(source_fiber, "tag", 0)
    from .ReactFiberLane import NoLanes

    if tag in (0, 1, 15):  # FunctionComponent, ClassComponent, SimpleMemoComponent
        current_source = source_fiber.alternate
        if current_source is not None:
            source_fiber.update_queue = getattr(current_source, "update_queue", None)
            source_fiber.memoized_state = getattr(
                current_source, "memoized_state", None
            )
            source_fiber.lanes = getattr(current_source, "lanes", NoLanes)
        else:
            source_fiber.update_queue = None
            source_fiber.memoized_state = None


def mark_suspense_boundary_should_capture(
    suspense_boundary: Any,
    return_fiber: Optional[Any],
    source_fiber: Any,
    root: Any,
    root_render_lanes: int,
) -> Optional[Any]:
    """
    标记 Suspense 边界需要捕获错误

    Args:
        suspense_boundary: Suspense 边界 Fiber
        return_fiber: 父 Fiber
        source_fiber: 源 Fiber
        root: FiberRoot
        root_render_lanes: 渲染的 lanes

    Returns:
        Suspense 边界 Fiber
    """
    from .ReactFiberLane import ConcurrentMode, NoMode
    from .ReactFiberWorkLoop import render_did_suspend, render_did_suspend_delay_if_possible

    # 检查是否是并发模式
    mode = getattr(suspense_boundary, "mode", NoMode)
    is_concurrent = (mode & ConcurrentMode) != NoMode

    if not is_concurrent:
        # Legacy 模式
        if suspense_boundary == return_fiber:
            # 特殊情况：在 Suspense 边界的 Offscreen wrapper 中挂起
            suspense_boundary.flags |= ShouldCapture
        else:
            suspense_boundary.flags |= DidCapture
            source_fiber.flags |= 1 << 16  # ForceUpdateForLegacySuspense

            # 清除生命周期标志
            source_fiber.flags &= ~(
                1 << 5 | 1 << 6 | 1 << 7 | 1 << 10 | Incomplete
            )  # Callback | Ref | Snapshot | UpdateLifeCycle | Incomplete

            # 如果是 ClassComponent，标记为 IncompleteClassComponent
            source_tag = getattr(source_fiber, "tag", 0)
            if source_tag == ClassComponent:
                current_source = getattr(source_fiber, "alternate", None)
                if current_source is None:
                    source_fiber.tag = 25  # IncompleteClassComponent
                else:
                    # 创建强制更新
                    update = create_update(SyncLane)
                    update.tag = 2  # ForceUpdate
                    from .ReactFiberClassUpdateQueue import enqueue_update
                    enqueue_update(source_fiber, update, SyncLane)

            # 标记为需要重新渲染
            source_fiber.lanes = mergeLanes(
                getattr(source_fiber, "lanes", NoLane), SyncLane
            )

        return suspense_boundary

    # 并发模式
    suspense_boundary.flags |= ShouldCapture
    suspense_boundary.lanes = root_render_lanes
    return suspense_boundary


def attach_ping_listener(root: Any, wakeable: Any, root_render_lanes: int) -> None:
    """
    附加 ping listener 到 wakeable

    当 wakeable resolve 时，触发重新渲染。

    Args:
        root: FiberRoot
        wakeable: wakeable 对象（Promise-like）
        root_render_lanes: 渲染的 lanes
    """
    # 简化实现：在实际的 React 中，这会创建一个 retry 函数
    # 并附加到 wakeable 的 then 回调
    # 这里我们只是记录

    def on_resolve(value: Any) -> None:
        # Wakeable 已解析，触发 retry
        # 实际实现会调度一个新的更新
        pass

    if hasattr(wakeable, "then") and callable(wakeable.then):
        try:
            wakeable.then(on_resolve)
        except Exception:
            pass


def mark_legacy_error_boundary_as_failed(instance: Any) -> None:
    """
    标记 legacy 错误边界为已失败

    用于防止无限重试。

    Args:
        instance: 组件实例
    """
    # 简化实现：在实际的 React 中，这会使用一个 WeakSet 来跟踪
    # 这里我们只是设置一个标记
    if hasattr(instance, "_already_failed"):
        instance._already_failed = True


def is_already_failed_legacy_error_boundary(instance: Any) -> bool:
    """
    检查 legacy 错误边界是否已失败

    Args:
        instance: 组件实例

    Returns:
        True 如果已失败
    """
    return getattr(instance, "_already_failed", False)


# =============================================================================
# 导出
# =============================================================================


__all__ = [
    # 核心函数
    "throw_exception",
    # 错误更新创建
    "create_root_error_update",
    "create_class_error_update",
    "initialize_class_error_update",
    # 辅助函数
    "reset_suspended_component",
    "mark_suspense_boundary_should_capture",
    "attach_ping_listener",
    "mark_legacy_error_boundary_as_failed",
    "is_already_failed_legacy_error_boundary",
]
