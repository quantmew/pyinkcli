"""
React Fiber Complete Work - Fiber 树构建的完成阶段

负责处理 Fiber 节点的 completeWork 阶段，包括：
- 完成 Fiber 节点的创建
- 构建 DOM 节点（或宿主环境节点）
- 收集副作用（side effects）
- 冒泡属性（bubble properties）到父节点
"""

from __future__ import annotations

from typing import Any, Optional

from .ReactFiberFlags import (
    ChildDeletion,
    DidCapture,
    ForceClientRender,
    Hydrating,
    MaySuspendCommit,
    NoFlags,
    Passive,
    Placement,
    Ref,
    ShouldSuspendCommit,
    Snapshot,
    StaticMask,
    Update,
    Visibility,
)
from .ReactFiberLane import NoLane, NoLanes, OffscreenLane, includesSomeLane, mergeLanes
from .ReactWorkTags import (
    ActivityComponent,
    ClassComponent,
    ContextConsumer,
    ContextProvider,
    ForwardRef,
    Fragment,
    FunctionComponent,
    HostComponent,
    HostRoot,
    HostText,
    LazyComponent,
    MemoComponent,
    Mode,
    OffscreenComponent,
    Profiler,
    SimpleMemoComponent,
    SuspenseComponent,
    SuspenseListComponent,
)


# =============================================================================
# 主 completeWork 函数
# =============================================================================


def complete_work(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> Optional[Any]:
    """
    completeWork - 完成 Fiber 节点的处理

    在 beginWork 之后调用，负责：
    1. 创建/更新宿主实例（DOM 节点等）
    2. 处理 Suspense 边界
    3. 收集副作用
    4. 冒泡子树属性

    Args:
        current: 当前的 Fiber 节点
        work_in_progress: 工作中的 Fiber 节点
        render_lanes: 渲染的 lanes

    Returns:
        sibling Fiber 或 None
    """
    # 更新 memoized_props
    work_in_progress.memoized_props = getattr(work_in_progress, "pending_props", None)

    # 根据组件类型处理
    work_tag = getattr(work_in_progress, "tag", 0)

    if work_tag == HostRoot:
        complete_host_root(current, work_in_progress, render_lanes)
    elif work_tag == HostComponent:
        complete_host_component(current, work_in_progress, render_lanes)
    elif work_tag == HostText:
        complete_host_text(current, work_in_progress, render_lanes)
    elif work_tag == FunctionComponent:
        complete_function_component(current, work_in_progress, render_lanes)
    elif work_tag == SimpleMemoComponent:
        complete_simple_memo_component(current, work_in_progress, render_lanes)
    elif work_tag == MemoComponent:
        complete_memo_component(current, work_in_progress, render_lanes)
    elif work_tag == ForwardRef:
        complete_forward_ref(current, work_in_progress, render_lanes)
    elif work_tag == Fragment:
        complete_fragment(current, work_in_progress, render_lanes)
    elif work_tag == ClassComponent:
        complete_class_component(current, work_in_progress, render_lanes)
    elif work_tag == SuspenseComponent:
        complete_suspense_component(current, work_in_progress, render_lanes)
    elif work_tag == OffscreenComponent:
        complete_offscreen_component(current, work_in_progress, render_lanes)
    elif work_tag == ContextProvider:
        complete_context_provider(current, work_in_progress, render_lanes)
    elif work_tag == ContextConsumer:
        complete_context_consumer(current, work_in_progress, render_lanes)
    elif work_tag == Profiler:
        complete_profiler(current, work_in_progress, render_lanes)
    elif work_tag == Mode:
        complete_mode(current, work_in_progress, render_lanes)
    elif work_tag == SuspenseListComponent:
        complete_suspense_list_component(current, work_in_progress, render_lanes)
    elif work_tag == ActivityComponent:
        complete_activity_component(current, work_in_progress, render_lanes)
    elif work_tag == LazyComponent:
        complete_lazy_component(current, work_in_progress, render_lanes)

    # 冒泡属性到父节点
    bubble_properties(work_in_progress)

    # 返回 sibling
    return getattr(work_in_progress, "sibling", None)


# =============================================================================
# 各种组件类型的 completeWork 实现
# =============================================================================


def complete_host_root(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> None:
    """
    完成 HostRoot 组件

    HostRoot 是应用的根容器。
    """
    # 更新 pending_props 到 memoized_props
    pending_props = getattr(work_in_progress, "pending_props", None)
    if pending_props is not None:
        work_in_progress.memoized_props = pending_props

    # 检查是否有子节点需要放置
    child = getattr(work_in_progress, "child", None)
    if child is not None:
        # 标记子节点需要放置
        child.flags |= Placement


def complete_host_component(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> None:
    """
    完成原生组件（如 div、span 等）

    负责创建/更新 DOM 节点。
    """
    from ..dom import createNode, setAttribute, setStyle, appendChildNode

    # 获取 props
    pending_props = getattr(work_in_progress, "pending_props", None) or {}

    if current is None:
        # 首次挂载：创建新节点
        node_type = getattr(work_in_progress, "type", "div")

        # 创建 DOM 节点
        instance = createNode(node_type)

        # 设置属性
        for key, value in pending_props.items():
            if key == "children" or key == "style":
                continue
            setAttribute(instance, key, value)

        # 设置样式
        style = pending_props.get("style")
        if style:
            setStyle(instance, style)

        # 存储实例
        work_in_progress.state_node = instance
        work_in_progress.flags |= Placement
    else:
        # 更新：检查 props 是否变化
        current_props = getattr(current, "memoized_props", {})

        if current_props != pending_props:
            work_in_progress.flags |= Update

            # 更新实例
            instance = getattr(work_in_progress, "state_node", None)
            if instance is None:
                instance = getattr(current, "state_node", None)
                work_in_progress.state_node = instance

            if instance is not None:
                # 更新属性
                for key, value in pending_props.items():
                    if key == "children" or key == "style":
                        continue
                    if key not in current_props or current_props[key] != value:
                        setAttribute(instance, key, value)

                # 更新样式
                current_style = current_props.get("style", {})
                new_style = pending_props.get("style", {})
                if current_style != new_style:
                    setStyle(instance, new_style)


def complete_host_text(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> None:
    """
    完成文本节点

    负责创建/更新文本节点。
    """
    from ..dom import createTextNode, setTextNodeValue

    pending_props = getattr(work_in_progress, "pending_props", None)

    if current is None:
        # 首次挂载
        text_content = pending_props if isinstance(pending_props, str) else str(pending_props or "")
        instance = createTextNode(text_content)
        work_in_progress.state_node = instance
        work_in_progress.flags |= Placement
    else:
        # 更新
        current_text = getattr(current, "memoized_props", "")
        if current_text != pending_props:
            work_in_progress.flags |= Update
            instance = getattr(work_in_progress, "state_node", None)
            if instance is None:
                instance = getattr(current, "state_node", None)
                work_in_progress.state_node = instance
            if instance is not None:
                setTextNodeValue(instance, pending_props or "")


def complete_function_component(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> None:
    """
    完成函数组件

    函数组件不创建实例，只需处理副作用。
    """
    # 检查是否有 Ref
    ref = getattr(work_in_progress, "ref", None)
    if ref is not None:
        work_in_progress.flags |= Ref

    # 检查是否有 useLayoutEffect 或 useEffect
    update_queue = getattr(work_in_progress, "update_queue", None)
    if update_queue is not None:
        last_effect = getattr(update_queue, "last_effect", None)
        if last_effect is not None:
            # 有待处理的被动效果
            work_in_progress.flags |= Passive


def complete_simple_memo_component(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> None:
    """
    完成 SimpleMemoComponent
    """
    complete_function_component(current, work_in_progress, render_lanes)


def complete_memo_component(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> None:
    """
    完成 MemoComponent (React.memo 包装的组件)
    """
    # MemoComponent 包装了另一个组件，传递 flags
    child = getattr(work_in_progress, "child", None)
    if child is not None:
        # 复用子节点的 flags
        work_in_progress.flags |= getattr(child, "flags", NoFlags)


def complete_forward_ref(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> None:
    """
    完成 ForwardRef 组件
    """
    complete_function_component(current, work_in_progress, render_lanes)


def complete_fragment(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> None:
    """
    完成 Fragment 组件

    Fragment 不创建任何实例，只需处理子节点。
    """
    # Fragment 不需要特殊处理
    pass


def complete_class_component(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> None:
    """
    完成类组件

    处理类组件的生命周期和副作用。
    """
    # 检查是否有 Ref
    ref = getattr(work_in_progress, "ref", None)
    if ref is not None:
        work_in_progress.flags |= Ref

    # 检查是否有 componentDidUpdate
    # TODO: 实现类组件的完整生命周期


def complete_suspense_component(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> None:
    """
    完成 Suspense 组件

    Suspense 用于处理异步加载和 fallback。
    """
    # 检查是否捕获了 suspended 状态
    did_capture = (getattr(work_in_progress, "flags", 0) & DidCapture) != NoFlags

    if did_capture:
        # 标记需要强制客户端渲染
        work_in_progress.flags |= ForceClientRender
        work_in_progress.flags &= ~DidCapture

    # 检查是否需要显示 fallback
    pending_props = getattr(work_in_progress, "pending_props", {})
    fallback = pending_props.get("fallback")
    children = pending_props.get("children")

    # 检查当前是否有 suspended 的子节点
    memoized_state = getattr(work_in_progress, "memoized_state", None)
    is_suspended = False

    if memoized_state is not None:
        is_suspended = memoized_state.get("is_suspended", False)

    if is_suspended and fallback is not None:
        # 显示 fallback
        # 标记需要放置 fallback 子节点
        child = getattr(work_in_progress, "child", None)
        if child is not None:
            child.flags |= Placement

    # 设置 memoized_state
    work_in_progress.memoized_state = {
        "is_suspended": is_suspended,
        "did_capture": did_capture,
    }


def complete_offscreen_component(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> None:
    """
    完成 Offscreen 组件

    Offscreen 用于隐藏不 visible 的子树。
    """
    pending_props = getattr(work_in_progress, "pending_props", {})
    mode = pending_props.get("mode", "visible")

    # 检查是否是 hidden 模式
    is_hidden = mode == "hidden"

    # 创建 Offscreen 实例
    if getattr(work_in_progress, "state_node", None) is None:
        work_in_progress.state_node = {
            "_visibility": "visible" if not is_hidden else "hidden",
            "_pending_markers": None,
            "_retry_cache": None,
        }

    # 设置 memoized_state
    work_in_progress.memoized_state = {
        "base_lanes": NoLanes,
        "cache_pool": None,
        "mode": mode,
    }

    # 如果 hidden，标记 visibility 变化
    if is_hidden:
        work_in_progress.flags |= Visibility


def complete_context_provider(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> None:
    """
    完成 Context Provider

    检查 context 值是否变化。
    """
    pending_props = getattr(work_in_progress, "pending_props", {})
    new_context = pending_props.get("value")

    # 检查 context 是否变化
    if current is not None:
        current_props = getattr(current, "memoized_props", {})
        old_context = current_props.get("value")

        if old_context != new_context:
            # Context 变化，需要通知消费者
            # TODO: 标记需要更新消费者
            pass


def complete_context_consumer(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> None:
    """
    完成 Context Consumer
    """
    # Consumer 不需要特殊处理
    pass


def complete_profiler(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> None:
    """
    完成 Profiler 组件
    """
    # Profiler 用于性能分析，不创建实例
    pass


def complete_mode(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> None:
    """
    完成 Mode 组件（如 StrictMode、ConcurrentMode）
    """
    # Mode 不创建实例
    pass


def complete_suspense_list_component(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> None:
    """
    完成 SuspenseList 组件
    """
    # TODO: 实现 SuspenseList 的完整逻辑
    pass


def complete_activity_component(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> None:
    """
    完成 Activity 组件
    """
    # Activity 是 Suspense 的变体
    pass


def complete_lazy_component(
    current: Optional[Any],
    work_in_progress: Any,
    render_lanes: int,
) -> None:
    """
    完成 Lazy 组件
    """
    # TODO: 实现 Lazy 组件的加载逻辑
    pass


# =============================================================================
# 辅助函数
# =============================================================================


def bubble_properties(work_in_progress: Any) -> None:
    """
    冒泡子树的属性到父节点

    收集子树的副作用和 lanes，向上传播。
    """
    subtree_flags = NoFlags
    child_lanes = NoLanes

    child = getattr(work_in_progress, "child", None)
    while child is not None:
        # 收集子节点的 flags
        child_flags = getattr(child, "flags", NoFlags)
        child_subtree_flags = getattr(child, "subtree_flags", NoFlags)
        subtree_flags |= child_flags | child_subtree_flags

        # 收集子节点的 lanes
        child_lanes |= getattr(child, "lanes", NoLanes)
        child_lanes |= getattr(child, "child_lanes", NoLanes)

        # 移动到下一个 sibling
        child = getattr(child, "sibling", None)

    # 设置 subtree_flags 和 child_lanes
    work_in_progress.subtree_flags = subtree_flags
    work_in_progress.child_lanes = child_lanes


def bubble_properties_with_parent_check(
    current: Optional[Any],
    work_in_progress: Any,
) -> bool:
    """
    检查子树是否需要克隆（用于持久化模式）

    Returns:
        True 如果需要克隆子树
    """
    # 检查是否 bailout
    did_bailout = current is not None and getattr(current, "child", None) == getattr(
        work_in_progress, "child", None
    )

    if did_bailout:
        return False

    # 检查是否有子节点删除
    if (getattr(work_in_progress, "flags", 0) & ChildDeletion) != NoFlags:
        return True

    # 检查子树是否有副作用
    child = getattr(work_in_progress, "child", None)
    checked_flags = Cloned | Visibility | Placement | ChildDeletion
    while child is not None:
        child_flags = getattr(child, "flags", NoFlags)
        child_subtree_flags = getattr(child, "subtree_flags", NoFlags)

        if (child_flags & checked_flags) != NoFlags or (
            child_subtree_flags & checked_flags
        ) != NoFlags:
            return True

        child = getattr(child, "sibling", None)

    return False


# =============================================================================
# 完整的 completeTree 函数
# =============================================================================


def complete_tree(current: Optional[Any], root: Any, render_lanes: int) -> dict[str, Any]:
    """
    完成整棵 Fiber 树的处理

    从 root 开始，递归处理所有子节点。

    Args:
        current: 当前的 root Fiber
        root: 工作中的 root Fiber
        render_lanes: 渲染的 lanes

    Returns:
        完成状态信息
    """
    contains_suspended = False

    def walk(node: Optional[Any]) -> None:
        nonlocal contains_suspended

        if node is None:
            return

        # 检查是否是 Suspense 组件且处于 suspended 状态
        if getattr(node, "tag", None) == SuspenseComponent:
            memoized_state = getattr(node, "memoized_state", None)
            if memoized_state is not None and memoized_state.get("is_suspended", False):
                contains_suspended = True

        # 调用 completeWork
        current_fiber = getattr(node, "alternate", None)
        complete_work(current_fiber, node, render_lanes)

        # 清除工作标志
        if hasattr(node, "is_work_in_progress"):
            node.is_work_in_progress = False

        # 递归处理子节点
        walk(getattr(node, "child", None))
        walk(getattr(node, "sibling", None))

    # 从 root 的 child 开始遍历
    root_child = getattr(root, "child", None)
    walk(root_child)

    # 完成 root
    complete_work(current, root, render_lanes)

    # 设置 root 的状态
    if getattr(root, "tag", None) == HostRoot:
        root.contains_suspended_fibers = contains_suspended
        root.memoized_state = {"contains_suspended_fibers": contains_suspended}

    # 清除工作标志
    if hasattr(root, "is_work_in_progress"):
        root.is_work_in_progress = False

    return {
        "containsSuspendedFibers": contains_suspended,
    }


# =============================================================================
# 导出
# =============================================================================


__all__ = [
    # 主函数
    "complete_work",
    "complete_tree",
    # 组件类型处理
    "complete_host_root",
    "complete_host_component",
    "complete_host_text",
    "complete_function_component",
    "complete_simple_memo_component",
    "complete_memo_component",
    "complete_forward_ref",
    "complete_fragment",
    "complete_class_component",
    "complete_suspense_component",
    "complete_offscreen_component",
    "complete_context_provider",
    "complete_context_consumer",
    "complete_profiler",
    "complete_mode",
    "complete_suspense_list_component",
    "complete_activity_component",
    "complete_lazy_component",
    # 辅助函数
    "bubble_properties",
    "bubble_properties_with_parent_check",
    # 兼容性别名（驼峰命名）
    "completeWork",
    "completeTree",
    "bubbleProperties",
]

# =============================================================================
# 兼容性别名（驼峰命名，用于向后兼容）
# =============================================================================

# 驼峰命名别名，用于与旧代码和测试兼容
completeWork = complete_work
completeTree = complete_tree
bubbleProperties = bubble_properties
