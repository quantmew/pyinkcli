"""
React Fiber Begin Work - Fiber 树构建的开始阶段

负责处理 Fiber 节点的 beginWork 阶段，包括：
- Props 和 Context 变更检测
- Bailout 优化（跳过未变化的子树）
- 根据组件类型分发到不同的 update 函数
- 协调（reconcile）子节点
"""

from __future__ import annotations

from typing import Any, Optional

from .ReactFiberFlags import (
    DidCapture,
    ForceUpdateForLegacySuspense,
    NoFlags,
    PerformedWork,
    Placement,
    Ref,
    Update,
)
from .ReactFiberLane import (
    NoLane,
    NoLanes,
    OffscreenLane,
    includesSomeLane,
    mergeLanes,
    removeLanes,
)
from .ReactWorkTags import (
    ClassComponent,
    ForwardRef,
    Fragment,
    FunctionComponent,
    HostComponent,
    HostRoot,
    HostText,
    MemoComponent,
    OffscreenComponent,
    SimpleMemoComponent,
    SuspenseComponent,
)
from .ReactFiberConcurrentUpdates import (
    enqueue_concurrent_render_for_lane,
    get_concurrently_updated_lanes,
)

# =============================================================================
# 全局状态
# =============================================================================

_did_receive_update: bool = False


def reset_did_receive_update() -> None:
    """重置 didReceiveUpdate 标志"""
    global _did_receive_update
    _did_receive_update = False


def get_did_receive_update() -> bool:
    """获取 didReceiveUpdate 标志"""
    return _did_receive_update


def _mark_did_receive_update(flag: bool) -> None:
    """设置 didReceiveUpdate 标志"""
    global _did_receive_update
    _did_receive_update = flag


# =============================================================================
# 子节点协调
# =============================================================================


def reconcile_children(
    current: Optional[Any],
    work_in_progress: Any,
    next_children: Any,
    render_lanes: int,
) -> None:
    """
    协调（reconcile）子节点

    根据 current 是否存在来决定使用 mount 还是 update 模式。

    Args:
        current: 当前的 Fiber 节点（如果是首次渲染则为 None）
        work_in_progress: 工作中的 Fiber 节点
        next_children: 新的子节点
        render_lanes: 渲染的 lanes
    """
    if current is None:
        # 首次挂载：不需要跟踪副作用，直接 mount 所有子节点
        work_in_progress.child = mount_child_fibers(
            work_in_progress,
            None,
            next_children,
            render_lanes,
        )
    else:
        # 更新：需要比较新旧子节点
        work_in_progress.child = reconcile_child_fibers(
            work_in_progress,
            current.child,
            next_children,
            render_lanes,
        )


def mount_child_fibers(
    work_in_progress: Any,
    current_child: Optional[Any],
    next_children: Any,
    render_lanes: int,
) -> Optional[Any]:
    """
    Mount 子节点 Fiber

    首次渲染时使用，不跟踪副作用。
    """
    return _reconcile_child_fibers_impl(
        work_in_progress,
        current_child,
        next_children,
        render_lanes,
        should_track_side_effects=False,
    )


def reconcile_child_fibers(
    work_in_progress: Any,
    current_child: Optional[Any],
    next_children: Any,
    render_lanes: int,
) -> Optional[Any]:
    """
    Reconcile 子节点 Fiber

    更新时使用，需要跟踪副作用。
    """
    return _reconcile_child_fibers_impl(
        work_in_progress,
        current_child,
        next_children,
        render_lanes,
        should_track_side_effects=True,
    )


def _reconcile_child_fibers_impl(
    work_in_progress: Any,
    current_child: Optional[Any],
    next_children: Any,
    render_lanes: int,
    should_track_side_effects: bool,
) -> Optional[Any]:
    """
    Reconcile 子节点的底层实现

    这是一个简化版本，实际实现需要完整的 Diff 算法。
    """
    # TODO: 实现完整的 React Child Reconciler
    # 目前返回一个简化实现

    if next_children is None:
        return None

    # 如果是单个元素，创建单个 Fiber
    if not isinstance(next_children, (list, tuple)):
        # 单个子节点
        child_fiber = create_child_fiber(
            work_in_progress,
            current_child,
            next_children,
            render_lanes,
        )
        if should_track_side_effects and current_child is not None:
            if child_fiber is not None:
                child_fiber.flags |= Update
        return child_fiber

    # 多个子节点
    # TODO: 实现完整的数组 Diff 算法
    if len(next_children) == 0:
        return None

    # 简化处理：只创建第一个子节点
    first_child = next_children[0] if next_children else None
    return create_child_fiber(
        work_in_progress,
        current_child.child if current_child else None,
        first_child,
        render_lanes,
    )


def create_child_fiber(
    work_in_progress: Any,
    current_child: Optional[Any],
    element: Any,
    render_lanes: int,
) -> Optional[Any]:
    """
    创建子 Fiber 节点

    根据 element 类型创建对应的 Fiber。
    """
    from . import ReactFiberNewContext as new_context

    if element is None:
        return None

    # 创建新的 Fiber 节点
    # TODO: 使用完整的 createFiber 函数
    child = type("Fiber", (), {})()
    child.tag = _get_work_tag_for_element(element)
    child.type = getattr(element, "type", None) or (
        element if not callable(element) else None
    )
    child.key = getattr(element, "key", None)
    child.pending_props = getattr(element, "props", None)
    child.memoized_props = getattr(current_child, "memoized_props", None) if current_child else None
    child.lanes = render_lanes
    child.child_lanes = NoLanes
    child.flags = NoFlags
    child.subtree_flags = NoFlags
    child.return_fiber = work_in_progress
    child.child = None
    child.sibling = None
    child.state_node = None
    child.memoized_state = None
    child.update_queue = None
    child.dependencies = None
    child.alternate = current_child

    # 如果有 current，复用 state_node
    if current_child is not None:
        child.state_node = getattr(current_child, "state_node", None)

    return child


def _get_work_tag_for_element(element: Any) -> int:
    """
    根据 element 获取 WorkTag

    TODO: 使用完整的 ReactWorkTags 系统。
    """
    if element is None or isinstance(element, bool):
        return Fragment

    if isinstance(element, str):
        return HostText

    if isinstance(element, (list, tuple)):
        return Fragment

    # 检查是否是 React 元素
    if hasattr(element, "type"):
        element_type = element.type
        if element_type is None:
            return HostComponent

        # 检查是否是字符串（原生组件）
        if isinstance(element_type, str):
            return HostComponent

        # 检查是否是函数组件
        if callable(element_type):
            return FunctionComponent

        # 检查是否是类组件
        if hasattr(element_type, "render"):
            return ClassComponent

    # 检查是否可直接渲染
    if callable(element):
        return FunctionComponent

    return HostComponent


# =============================================================================
# Bailout 优化
# =============================================================================


def bailout_on_already_finished_work(
    current: Any,
    work_in_progress: Any,
    render_lanes: int,
) -> Optional[Any]:
    """
    Bailout：跳过已经完成的工作

    当 props、context 都没有变化，且没有待处理的更新时，
    可以跳过该 Fiber 节点的处理，直接复用之前的结果。

    Args:
        current: 当前的 Fiber 节点
        work_in_progress: 工作中的 Fiber 节点
        render_lanes: 渲染的 lanes

    Returns:
        子节点 Fiber 或 None
    """
    # 重置 work_in_progress 的 lanes
    work_in_progress.lanes = getattr(current, "lanes", NoLanes)

    # 检查是否有未处理的子节点更新
    child_lanes = getattr(current, "child_lanes", NoLanes)
    if child_lanes != NoLanes and includesSomeLane(render_lanes, child_lanes):
        # 子树有待处理的更新，不能 bailout
        return work_in_progress.child

    # 可以 bailout，返回 null 表示不需要处理子节点
    return None


def check_scheduled_update_or_context(
    current: Any,
    render_lanes: int,
) -> bool:
    """
    检查是否有待处理的更新或 context 变化

    Returns:
        True 如果有待处理的更新或 context 变化
    """
    # 检查 lanes
    if includes_some_lane(getattr(current, "lanes", NoLanes), render_lanes):
        return True

    # 检查 child_lanes
    if includes_some_lane(getattr(current, "child_lanes", NoLanes), render_lanes):
        return True

    # 检查 context 依赖
    dependencies = getattr(current, "dependencies", None)
    if dependencies is not None:
        from . import ReactFiberNewContext as new_context
        if new_context.check_if_context_changed(dependencies):
            return True

    return False


# =============================================================================
# update 函数 - 各种组件类型的处理
# =============================================================================


def update_host_root(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> Optional[Any]:
    """
    更新 HostRoot 组件

    HostRoot 是应用的最顶层容器。
    """
    # 准备读取 context
    from . import ReactFiberNewContext as new_context
    new_context.prepare_to_read_context(work_in_progress, render_lanes)

    # 获取 pending props
    pending_props = getattr(work_in_progress, "pending_props", None)
    if pending_props is None:
        # 没有 pending props，尝试从当前节点获取
        if current is not None:
            pending_props = getattr(current, "memoized_props", None)

    if pending_props is not None:
        # 协调子节点
        reconcile_children(current, work_in_progress, pending_props, render_lanes)

    # 标记已执行工作
    work_in_progress.flags |= PerformedWork

    return work_in_progress.child


def update_function_component(
    current: Optional[Any],
    work_in_progress: Any,
    component: Any,
    next_props: Any,
    render_lanes: int,
) -> Optional[Any]:
    """
    更新函数组件

    执行函数组件并获取渲染结果。
    """
    from . import ReactFiberHooks as fiber_hooks
    from . import ReactFiberNewContext as new_context

    # 准备读取 context
    new_context.prepare_to_read_context(work_in_progress, render_lanes)

    # 使用 hooks 渲染组件
    if current is not None and not _did_receive_update:
        # 没有更新，可以 bailout
        from .ReactFiberHooks import bailout_hooks
        bailout_hooks(current, work_in_progress, render_lanes)
        return bailout_on_already_finished_work(current, work_in_progress, render_lanes)

    # 渲染组件
    next_children = fiber_hooks.render_with_hooks(
        current,
        work_in_progress,
        component,
        next_props,
        render_lanes,
    )

    # 标记已执行工作
    work_in_progress.flags |= PerformedWork

    # 协调子节点
    reconcile_children(current, work_in_progress, next_children, render_lanes)

    return work_in_progress.child


def update_simple_memo_component(
    current: Optional[Any],
    work_in_progress: Any,
    component: Any,
    next_props: Any,
    render_lanes: int,
) -> Optional[Any]:
    """
    更新 SimpleMemoComponent

    使用浅比较来优化 re-render。
    """
    if current is not None:
        prev_props = getattr(current, "memoized_props", None)

        # 浅比较 props
        if _shallow_equal(prev_props, next_props):
            # props 相同，检查 ref
            current_ref = getattr(current, "ref", None)
            work_in_progress_ref = getattr(work_in_progress, "ref", None)

            if current_ref == work_in_progress_ref:
                # props 和 ref 都相同，可以 bailout
                _mark_did_receive_update(False)

                # 复用之前的 props 对象
                work_in_progress.pending_props = prev_props

                # 检查是否有待处理的更新
                if not check_scheduled_update_or_context(current, render_lanes):
                    work_in_progress.lanes = getattr(current, "lanes", NoLanes)
                    return bailout_on_already_finished_work(
                        current, work_in_progress, render_lanes
                    )

    # props 变化或首次渲染，当作函数组件处理
    return update_function_component(
        current,
        work_in_progress,
        component,
        next_props,
        render_lanes,
    )


def update_memo_component(
    current: Optional[Any],
    work_in_progress: Any,
    component: Any,
    next_props: Any,
    render_lanes: int,
) -> Optional[Any]:
    """
    更新 MemoComponent (React.memo 包装的组件)
    """
    if current is None:
        # 首次挂载
        # 创建子 Fiber
        child_type = getattr(component, "type", component)
        child = create_child_fiber(
            work_in_progress,
            None,
            {"type": child_type, "props": next_props},
            render_lanes,
        )
        if child is not None:
            child.ref = getattr(work_in_progress, "ref", None)
            child.return_fiber = work_in_progress
            work_in_progress.child = child
        return child

    # 更新
    current_child = getattr(current, "child", None)
    if current_child is None:
        return None

    # 检查是否有待处理的更新
    has_scheduled_update = check_scheduled_update_or_context(current, render_lanes)

    if not has_scheduled_update:
        # 没有待处理的更新，进行浅比较
        prev_props = getattr(current_child, "memoized_props", None)
        compare_fn = getattr(component, "compare", _shallow_equal)

        if compare_fn(prev_props, next_props):
            # props 相同，检查 ref
            current_ref = getattr(current, "ref", None)
            work_in_progress_ref = getattr(work_in_progress, "ref", None)

            if current_ref == work_in_progress_ref:
                # 可以 bailout
                _mark_did_receive_update(False)
                return bailout_on_already_finished_work(
                    current, work_in_progress, render_lanes
                )

    # props 变化，创建新的 child
    work_in_progress.flags |= PerformedWork
    new_child = create_work_in_progress(current_child, next_props)
    new_child.ref = getattr(work_in_progress, "ref", None)
    new_child.return_fiber = work_in_progress
    work_in_progress.child = new_child
    return new_child


def update_forward_ref(
    current: Optional[Any],
    work_in_progress: Any,
    component: Any,
    next_props: Any,
    render_lanes: int,
) -> Optional[Any]:
    """
    更新 ForwardRef 组件
    """
    render_fn = getattr(component, "render", component)
    ref = getattr(work_in_progress, "ref", None)

    # 处理 props（移除 ref）
    props_without_ref = next_props
    if isinstance(next_props, dict) and "ref" in next_props:
        props_without_ref = {k: v for k, v in next_props.items() if k != "ref"}

    # 使用 hooks 渲染
    from . import ReactFiberHooks as fiber_hooks

    next_children = fiber_hooks.render_with_hooks(
        current,
        work_in_progress,
        render_fn,
        props_without_ref,
        ref,
        render_lanes,
    )

    # 标记已执行工作
    work_in_progress.flags |= PerformedWork

    # 协调子节点
    reconcile_children(current, work_in_progress, next_children, render_lanes)

    return work_in_progress.child


def update_host_component(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> Optional[Any]:
    """
    更新原生组件（如 div、span 等）
    """
    # 原生组件不需要特殊处理，只需协调子节点
    next_props = getattr(work_in_progress, "pending_props", None)
    next_children = getattr(next_props, "children", None) if next_props else None

    if next_children is not None:
        reconcile_children(current, work_in_progress, next_children, render_lanes)

    work_in_progress.flags |= PerformedWork

    return work_in_progress.child


def update_suspense_component(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> Optional[Any]:
    """
    更新 Suspense 组件

    Suspense 用于处理异步加载和 fallback。
    """
    # 检查是否捕获了 suspended 状态
    did_suspend = (getattr(work_in_progress, "flags", 0) & DidCapture) != NoFlags

    if did_suspend:
        # 清除 DidCapture 标志，准备重试
        work_in_progress.flags &= ~DidCapture

        # TODO: 处理 suspended 状态的重试逻辑
        # 目前简化处理：继续渲染 primary children
        pass

    # 获取子节点
    next_props = getattr(work_in_progress, "pending_props", None)
    if next_props is None:
        next_props = {}

    # 渲染 primary children 或 fallback
    # TODO: 实现完整的 Suspense 逻辑
    primary_children = next_props.get("children")
    fallback = next_props.get("fallback")

    # 简化处理：始终渲染 primary children
    reconcile_children(current, work_in_progress, primary_children, render_lanes)

    work_in_progress.flags |= PerformedWork

    return work_in_progress.child


def update_offscreen_component(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> Optional[Any]:
    """
    更新 Offscreen 组件

    Offscreen 用于隐藏不 visible 的子树。
    """
    next_props = getattr(work_in_progress, "pending_props", None)
    if next_props is None:
        next_props = {}

    next_children = next_props.get("children")
    next_mode = next_props.get("mode", "visible")

    # 检查是否是 hidden 模式
    is_hidden = next_mode == "hidden"

    if is_hidden:
        # hidden 模式：使用 OffscreenLane 渲染
        work_in_progress.lanes = OffscreenLane

    # 协调子节点
    reconcile_children(current, work_in_progress, next_children, render_lanes)

    work_in_progress.flags |= PerformedWork

    return work_in_progress.child


def update_class_component(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> Optional[Any]:
    """
    更新类组件

    这是类组件更新的主入口，处理：
    - 实例构造（首次挂载）
    - shouldComponentUpdate 检查
    - 状态更新
    - render() 调用
    - 子节点协调

    Args:
        current: 当前 Fiber
        work_in_progress: 工作中的 Fiber
        render_lanes: 渲染的 lanes

    Returns:
        下一个要处理的 Fiber
    """
    from .ReactFiberClassUpdateQueue import process_update_queue, UpdateQueue
    from .ReactFiberNewContext import prepare_to_read_context, propagate_context_change

    component_type = getattr(work_in_progress, "type", None)
    if component_type is None:
        return None

    # 准备读取 context
    prepare_to_read_context(work_in_progress, render_lanes)

    # 获取或创建实例
    instance = getattr(work_in_progress, "state_node", None)
    pending_props = getattr(work_in_progress, "pending_props", None)

    should_update = False

    if instance is None:
        # 首次挂载：构造实例
        if current is None:
            # 全新的挂载
            construct_class_instance(work_in_progress, component_type, pending_props)
            instance = getattr(work_in_progress, "state_node", None)
            mount_class_instance(work_in_progress, component_type, pending_props, render_lanes)
            should_update = True
        else:
            # 恢复挂载（resume mount）
            resume_mount_class_instance(work_in_progress, component_type, pending_props, render_lanes)
            instance = getattr(work_in_progress, "state_node", None)
            should_update = True
    elif current is None:
        # 没有 current 但有实例，恢复挂载
        resume_mount_class_instance(work_in_progress, component_type, pending_props, render_lanes)
        should_update = True
    else:
        # 更新现有实例
        should_update = update_class_instance(
            current, work_in_progress, component_type, pending_props, render_lanes
        )

    # 完成类组件的更新
    return finish_class_component(
        current,
        work_in_progress,
        component_type,
        should_update,
        render_lanes,
    )


def construct_class_instance(
    work_in_progress: Any,
    component_type: type,
    pending_props: Any,
) -> None:
    """
    构造类组件实例

    Args:
        work_in_progress: 工作中的 Fiber
        component_type: 组件类
        pending_props: Props
    """
    # 调用构造函数
    try:
        instance = component_type(pending_props)
        work_in_progress.state_node = instance

        # 设置 updater
        if not hasattr(instance, "updater"):
            instance.updater = ClassComponentUpdater()

        # 初始化 state
        if not hasattr(instance, "state"):
            instance.state = None

    except Exception as e:
        # 构造过程中抛出错误
        raise


def mount_class_instance(
    work_in_progress: Any,
    component_type: type,
    pending_props: Any,
    render_lanes: int,
) -> None:
    """
    Mount 类组件实例

    调用 componentWillMount（如果定义）并设置初始状态。

    Args:
        work_in_progress: 工作中的 Fiber
        component_type: 组件类
        pending_props: Props
        render_lanes: 渲染的 lanes
    """
    instance = work_in_progress.state_node

    # 处理更新队列
    queue = getattr(work_in_progress, "update_queue", None)
    if queue is not None:
        result = process_update_queue(work_in_progress, instance, pending_props, None)
        instance.state = result["state"]

    # 调用 componentWillMount（如果定义了）
    if hasattr(instance, "componentWillMount") and callable(instance.componentWillMount):
        # 注意：UNSAFE_componentWillMount 在严格模式下不应被调用
        # 这里简化实现
        pass

    # 初始化 state
    if instance.state is None:
        instance.state = {}


def resume_mount_class_instance(
    work_in_progress: Any,
    component_type: type,
    pending_props: Any,
    render_lanes: int,
) -> None:
    """
    恢复 Mount 类组件实例

    用于并发渲染的恢复。

    Args:
        work_in_progress: 工作中的 Fiber
        component_type: 组件类
        pending_props: Props
        render_lanes: 渲染的 lanes
    """
    # 简化实现：当作新的 mount 处理
    mount_class_instance(work_in_progress, component_type, pending_props, render_lanes)


def update_class_instance(
    current: Any,
    work_in_progress: Any,
    component_type: type,
    pending_props: Any,
    render_lanes: int,
) -> bool:
    """
    更新类组件实例

    调用 shouldComponentUpdate 和 componentWillUpdate（如果定义了）。

    Args:
        current: 当前 Fiber
        work_in_progress: 工作中的 Fiber
        component_type: 组件类
        pending_props: 新的 Props
        render_lanes: 渲染的 lanes

    Returns:
        True 如果需要更新，False 否则
    """
    instance = work_in_progress.state_node
    if instance is None:
        return True

    current_props = getattr(current, "memoized_props", None)
    current_state = getattr(current, "memoized_state", None)

    # 处理更新队列
    queue = getattr(work_in_progress, "update_queue", None)
    if queue is not None:
        result = process_update_queue(
            work_in_progress,
            instance,
            pending_props,
            getattr(instance, "state", None),
        )
        new_state = result["state"]
    else:
        new_state = getattr(instance, "state", None)

    # 检查 shouldComponentUpdate
    should_update = True

    if hasattr(instance, "shouldComponentUpdate") and callable(instance.shouldComponentUpdate):
        try:
            should_update = instance.shouldComponentUpdate(pending_props, new_state)
        except Exception:
            # 如果 shouldComponentUpdate 抛出错误，继续更新
            should_update = True

    # 调用 UNSAFE_componentWillUpdate（如果定义了）
    if should_update:
        if hasattr(instance, "componentWillUpdate") and callable(instance.componentWillUpdate):
            try:
                instance.componentWillUpdate(pending_props, new_state)
            except Exception:
                pass

        # 更新 props 和 state
        instance.props = pending_props
        instance.state = new_state

    return should_update


def finish_class_component(
    current: Optional[Any],
    work_in_progress: Any,
    component_type: type,
    should_update: bool,
    render_lanes: int,
) -> Optional[Any]:
    """
    完成类组件的更新

    处理 Ref、错误捕获、render() 调用和子节点协调。

    Args:
        current: 当前 Fiber
        work_in_progress: 工作中的 Fiber
        component_type: 组件类
        should_update: 是否需要更新
        render_lanes: 渲染的 lanes

    Returns:
        下一个要处理的 Fiber
    """
    from .ReactFiberFlags import DidCapture, PerformedWork

    # 处理 Ref
    mark_ref(current, work_in_progress)

    # 检查是否捕获了错误
    did_capture_error = (getattr(work_in_progress, "flags", 0) & DidCapture) != NoFlags

    # 如果不需要更新且没有捕获错误，bailout
    if not should_update and not did_capture_error:
        return bailout_on_already_finished_work(current, work_in_progress, render_lanes)

    instance = getattr(work_in_progress, "state_node", None)

    # 渲染组件
    if did_capture_error:
        # 捕获了错误，且没有定义 getDerivedStateFromError，unmount 子节点
        get_derived = getattr(component_type, "getDerivedStateFromError", None)
        if get_derived is None:
            # 清空子节点
            work_in_progress.child = None
            work_in_progress.flags |= PerformedWork
            return None

    # 调用 render()
    if instance is not None and hasattr(instance, "render") and callable(instance.render):
        try:
            next_children = instance.render()
        except Exception as e:
            # render() 抛出错误，重新抛出
            raise e
    else:
        # 没有 render 方法，返回 None
        next_children = None

    # 标记已执行工作
    work_in_progress.flags |= PerformedWork

    # 协调子节点
    if current is not None and did_capture_error:
        # 从错误中恢复，强制重新协调
        force_unmount_current_and_reconcile(
            current, work_in_progress, next_children, render_lanes
        )
    else:
        reconcile_children(current, work_in_progress, next_children, render_lanes)

    # Memoize state
    if instance is not None:
        work_in_progress.memoized_state = getattr(instance, "state", None)

    # Memoize props
    work_in_progress.memoized_props = pending_props

    return work_in_progress.child


def mark_ref(current: Optional[Any], work_in_progress: Any) -> None:
    """
    标记 Ref 是否需要更新

    Args:
        current: 当前 Fiber
        work_in_progress: 工作中的 Fiber
    """
    from .ReactFiberFlags import Ref

    ref = getattr(work_in_progress, "ref", None)

    if ref is None:
        # Ref 被清空
        if current is not None and getattr(current, "ref", None) is not None:
            work_in_progress.flags |= Ref
    else:
        # Ref 变化
        if current is None or getattr(current, "ref", None) != ref:
            work_in_progress.flags |= Ref


def force_unmount_current_and_reconcile(
    current: Any,
    work_in_progress: Any,
    next_children: Any,
    render_lanes: int,
) -> None:
    """
    强制 unmount 当前子节点并重新协调

    用于从错误中恢复时。

    Args:
        current: 当前 Fiber
        work_in_progress: 工作中的 Fiber
        next_children: 新的子节点
        render_lanes: 渲染的 lanes
    """
    # 简化实现：直接协调，不复用现有子节点
    work_in_progress.child = mount_child_fibers(
        work_in_progress,
        None,
        next_children,
        render_lanes,
    )


class ClassComponentUpdater:
    """
    类组件的 Updater

    用于 setState 和 forceUpdate。
    """

    def enqueue_set_state(self, instance: Any, partial_state: Any, callback: Any = None) -> None:
        """
        入队 setState 更新

        Args:
            instance: 组件实例
            partial_state: 部分状态（字典或返回字典的函数）
            callback: 更新完成后的回调
        """
        from .ReactFiberLane import DefaultLane
        from .ReactFiberClassUpdateQueue import Update, UpdateState, enqueue_update

        # 找到对应的 Fiber
        fiber = _get_fiber_for_instance(instance)
        if fiber is None:
            return

        # 创建更新对象
        update = Update(lane=DefaultLane, tag=UpdateState, payload=partial_state, callback=callback)

        # 入队
        enqueue_update(fiber, update, DefaultLane)

        # 调度更新
        from .ReactFiberWorkLoop import schedule_update_on_fiber
        schedule_update_on_fiber(fiber, DefaultLane, None)

    def enqueue_force_update(self, instance: Any, callback: Any = None) -> None:
        """
        入队 forceUpdate 更新

        Args:
            instance: 组件实例
            callback: 更新完成后的回调
        """
        from .ReactFiberLane import DefaultLane
        from .ReactFiberClassUpdateQueue import Update, ForceUpdate, enqueue_update

        fiber = _get_fiber_for_instance(instance)
        if fiber is None:
            return

        update = Update(lane=DefaultLane, tag=ForceUpdate, payload=None, callback=callback)
        enqueue_update(fiber, update, DefaultLane)

        from .ReactFiberWorkLoop import schedule_update_on_fiber
        schedule_update_on_fiber(fiber, DefaultLane, None)

    def enqueue_replace_state(self, instance: Any, state: Any, callback: Any = None) -> None:
        """
        入队 replaceState 更新

        Args:
            instance: 组件实例
            state: 新的状态
            callback: 更新完成后的回调
        """
        from .ReactFiberLane import DefaultLane
        from .ReactFiberClassUpdateQueue import Update, ReplaceState, enqueue_update

        fiber = _get_fiber_for_instance(instance)
        if fiber is None:
            return

        update = Update(lane=DefaultLane, tag=ReplaceState, payload=state, callback=callback)
        enqueue_update(fiber, update, DefaultLane)

        from .ReactFiberWorkLoop import schedule_update_on_fiber
        schedule_update_on_fiber(fiber, DefaultLane, None)


def _get_fiber_for_instance(instance: Any) -> Optional[Any]:
    """
    通过实例查找对应的 Fiber

    这是一个简化实现，实际 React 使用 FiberMap。

    Args:
        instance: 组件实例

    Returns:
        Fiber 或 None
    """
    # 尝试从实例获取 fiber 引用
    return getattr(instance, "_fiber", None)


# =============================================================================
# 辅助函数
# =============================================================================


def create_work_in_progress(current: Any, new_props: Any) -> Any:
    """
    创建 work-in-progress Fiber

    复用 current 的子节点，更新 props。
    """
    # 创建新的 Fiber 节点
    child = type("Fiber", (), {})()

    # 复制属性
    child.tag = getattr(current, "tag", 0)
    child.type = getattr(current, "type", None)
    child.key = getattr(current, "key", None)
    child.pending_props = new_props
    child.memoized_props = getattr(current, "memoized_props", None)
    child.lanes = getattr(current, "lanes", NoLanes)
    child.child_lanes = getattr(current, "child_lanes", NoLanes)
    child.flags = NoFlags
    child.subtree_flags = NoFlags
    child.return_fiber = getattr(current, "return_fiber", None)
    child.child = getattr(current, "child", None)
    child.sibling = getattr(current, "sibling", None)
    child.state_node = getattr(current, "state_node", None)
    child.memoized_state = getattr(current, "memoized_state", None)
    child.update_queue = getattr(current, "update_queue", None)
    child.dependencies = getattr(current, "dependencies", None)
    child.alternate = current

    return child


def _shallow_equal(a: Any, b: Any) -> bool:
    """
    浅比较两个对象

    用于 React.memo 的默认比较函数。
    """
    if a is b:
        return True

    if a is None or b is None:
        return False

    if type(a) != type(b):
        return False

    if isinstance(a, dict):
        if len(a) != len(b):
            return False
        for key in a:
            if key not in b or a[key] != b[key]:
                return False
        return True

    if isinstance(a, (list, tuple)):
        if len(a) != len(b):
            return False
        for i in range(len(a)):
            if a[i] != b[i]:
                return False
        return True

    return False


def includes_some_lane(a: int, b: int) -> bool:
    """检查是否包含共同的 lane"""
    return (a & b) != NoLanes


# =============================================================================
# 主 beginWork 函数
# =============================================================================


def begin_work(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> Optional[Any]:
    """
    beginWork - Fiber 处理的主入口

    这是 React Fiber 协调算法的核心部分。

    Args:
        current: 当前的 Fiber 节点（如果是首次渲染则为 None）
        work_in_progress: 工作中的 Fiber 节点
        render_lanes: 渲染的 lanes

    Returns:
        下一个要处理的 Fiber 节点（通常是第一个 child）
    """
    global _did_receive_update

    # 重置更新标志
    _did_receive_update = False

    # 获取组件类型和 props
    work_tag = getattr(work_in_progress, "tag", 0)
    pending_props = getattr(work_in_progress, "pending_props", None)

    # 如果是更新（current 存在），检查 props 是否变化
    if current is not None:
        old_props = getattr(current, "memoized_props", None)
        new_props = pending_props

        if old_props != new_props:
            _did_receive_update = True
        else:
            # Props 相同，检查是否有待处理的更新
            has_scheduled = check_scheduled_update_or_context(current, render_lanes)
            if not has_scheduled and (getattr(work_in_progress, "flags", 0) & DidCapture) == NoFlags:
                # 没有更新，可以 bailout
                _did_receive_update = False
                return attempt_early_bailout(current, work_in_progress, render_lanes)
            elif (getattr(current, "flags", 0) & ForceUpdateForLegacySuspense) != NoFlags:
                # 特殊情况：legacy suspense 强制更新
                _did_receive_update = True
            else:
                _did_receive_update = False
    else:
        # 首次挂载
        _did_receive_update = False

    # 清除 pending lanes
    work_in_progress.lanes = NoLanes

    # 根据组件类型分发
    try:
        if work_tag == HostRoot:
            return update_host_root(current, work_in_progress, render_lanes)

        elif work_tag == FunctionComponent:
            component_type = getattr(work_in_progress, "type", None)
            if component_type is not None:
                return update_function_component(
                    current, work_in_progress, component_type, pending_props, render_lanes
                )

        elif work_tag == SimpleMemoComponent:
            component_type = getattr(work_in_progress, "type", None)
            if component_type is not None:
                return update_simple_memo_component(
                    current, work_in_progress, component_type, pending_props, render_lanes
                )

        elif work_tag == MemoComponent:
            component_type = getattr(work_in_progress, "type", None)
            if component_type is not None:
                return update_memo_component(
                    current, work_in_progress, component_type, pending_props, render_lanes
                )

        elif work_tag == ForwardRef:
            component_type = getattr(work_in_progress, "type", None)
            if component_type is not None:
                return update_forward_ref(
                    current, work_in_progress, component_type, pending_props, render_lanes
                )

        elif work_tag == HostComponent:
            return update_host_component(current, work_in_progress, render_lanes)

        elif work_tag == HostText:
            # Text 节点不需要特殊处理
            work_in_progress.flags |= PerformedWork
            return None

        elif work_tag == SuspenseComponent:
            return update_suspense_component(current, work_in_progress, render_lanes)

        elif work_tag == OffscreenComponent:
            return update_offscreen_component(current, work_in_progress, render_lanes)

        elif work_tag == ClassComponent:
            return update_class_component(current, work_in_progress, render_lanes)

        elif work_tag == Fragment:
            # Fragment 只需协调子节点
            reconcile_children(current, work_in_progress, pending_props, render_lanes)
            work_in_progress.flags |= PerformedWork
            return work_in_progress.child

    except Exception as e:
        # 捕获异常并抛出到错误边界
        return handle_error_during_render(e, current, work_in_progress, render_lanes)

    # 默认：返回 child
    return getattr(work_in_progress, "child", None)


def handle_error_during_render(
    error: Exception,
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> Optional[Any]:
    """
    处理渲染过程中的错误

    Args:
        error: 抛出的错误
        current: 当前 Fiber
        work_in_progress: 工作中的 Fiber
        render_lanes: 渲染的 lanes

    Returns:
        下一个要处理的 Fiber 或 None
    """
    from .ReactFiberThrow import throw_exception
    from .ReactFiberWorkLoop import get_work_in_progress_root

    # 获取 root
    root = get_work_in_progress_root()

    if root is None:
        # 没有 root，重新抛出错误
        raise error

    # 获取 return fiber
    return_fiber = getattr(work_in_progress, "return_fiber", None)

    # 调用 throw_exception
    should_fatal = throw_exception(root, return_fiber, work_in_progress, error, render_lanes)

    if should_fatal:
        # 致命错误，重新抛出
        raise error

    # 返回 bailout，继续渲染错误边界
    return bailout_on_already_finished_work(current, work_in_progress, render_lanes)


def attempt_early_bailout(
    current: Any,
    work_in_progress: Any,
    render_lanes: int,
) -> Optional[Any]:
    """
    尝试提前 bailout

    检查子树是否有待处理的更新，如果没有则可以跳过。
    """
    # 检查 child_lanes
    child_lanes = getattr(current, "child_lanes", NoLanes)

    if child_lanes != NoLanes and includes_some_lane(render_lanes, child_lanes):
        # 子树有待处理的更新，不能 bailout
        return work_in_progress.child

    # 可以 bailout
    return bailout_on_already_finished_work(current, work_in_progress, render_lanes)


# =============================================================================
# 导出
# =============================================================================


__all__ = [
    # 主函数
    "begin_work",
    "handle_error_during_render",
    # 子节点协调
    "reconcile_children",
    "mount_child_fibers",
    "reconcile_child_fibers",
    # Bailout
    "bailout_on_already_finished_work",
    "check_scheduled_update_or_context",
    "attempt_early_bailout",
    # Update 函数
    "update_host_root",
    "update_function_component",
    "update_simple_memo_component",
    "update_memo_component",
    "update_forward_ref",
    "update_host_component",
    "update_suspense_component",
    "update_offscreen_component",
    "update_class_component",
    # 辅助函数
    "create_work_in_progress",
    "create_child_fiber",
    # 状态
    "reset_did_receive_update",
    "get_did_receive_update",
    # 兼容性别名（驼峰命名）
    "beginWork",
    "checkIfWorkInProgressReceivedUpdate",
    "resetWorkInProgressReceivedUpdate",
]

# =============================================================================
# 兼容性别名（驼峰命名，用于向后兼容）
# =============================================================================

# 驼峰命名别名，用于与旧代码和测试兼容
beginWork = begin_work


def checkIfWorkInProgressReceivedUpdate() -> bool:
    """兼容性别名：检查 workInProgree 是否收到更新"""
    return get_did_receive_update()


def resetWorkInProgressReceivedUpdate() -> None:
    """兼容性别名：重置 workInProgress 收到更新的标志"""
    reset_did_receive_update()
