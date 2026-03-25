"""
React Fiber Commit Work - Fiber 树的提交阶段

负责处理 Fiber 树的 commit 阶段，包括：
- Before Mutation 阶段：读取 DOM 快照
- Mutation 阶段：应用 DOM 变更
- Layout Effects 阶段：执行 useLayoutEffect 和 componentDidMount
- Passive Effects 阶段：执行 useEffect

这是同步执行的阶段，不可中断。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .ReactFiberFlags import (
    Callback,
    ChildDeletion,
    ContentReset,
    Deletion,
    DidCapture,
    HasSnapshot,
    Hydrating,
    LayoutMask,
    MaySuspendCommit,
    MutationMask,
    NoFlags,
    Passive,
    PassiveDestroy,
    PassiveUnmount,
    PassiveUpdate,
    Placement,
    Ref,
    ShouldSuspendCommit,
    Snapshot,
    Update,
)
from .ReactFiberLane import NoLanes, mergeLanes
from .ReactWorkTags import (
    ClassComponent,
    ForwardRef,
    Fragment,
    FunctionComponent,
    HostComponent,
    HostPortal,
    HostRoot,
    HostText,
    MemoComponent,
    OffscreenComponent,
    SimpleMemoComponent,
    SuspenseComponent,
)

# =============================================================================
# 数据结构
# =============================================================================


@dataclass
class CommitList:
    """提交阶段需要执行的效果列表"""

    # 布局效果
    layout_effects: list = field(default_factory=list)

    # DOM 变更
    placements: list = field(default_factory=list)  # 放置节点
    updates: list = field(default_factory=list)  # 更新节点
    deletions: list = field(default_factory=list)  # 删除节点
    content_resets: list = field(default_factory=list)  # 重置内容

    # Ref 效果
    ref_callbacks: list = field(default_factory=list)  # Ref 回调

    # 被动效果
    passive_mount_effects: list = field(default_factory=list)  # 挂载被动效果
    passive_unmount_effects: list = field(default_factory=list)  # 卸载被动效果


@dataclass
class PreparedCommit:
    """
    已准备的提交

    包含 commit 阶段需要执行的所有效果。
    """

    work_root: Any  # 工作中的 root Fiber
    commit_list: CommitList  # 效果列表
    root_completion_state: Optional[dict] = None  # Root 完成状态
    passive_effect_state: Optional[dict] = None  # 被动效果状态


# =============================================================================
# 全局状态
# =============================================================================

_offscreen_subtree_is_hidden: bool = False
_offscreen_subtree_was_hidden: bool = False
_next_effect: Optional[Any] = None


# =============================================================================
# Commit 阶段入口
# =============================================================================


def commit_root(root: Any, committed_lanes: int) -> PreparedCommit:
    """
    提交 Root

    这是 commit 阶段的主入口，负责协调所有 commit 效果。

    Args:
        root: Fiber Root
        committed_lanes: 提交的 lanes

    Returns:
        PreparedCommit 对象
    """
    global _offscreen_subtree_is_hidden, _offscreen_subtree_was_hidden

    # 重置状态
    _offscreen_subtree_is_hidden = False
    _offscreen_subtree_was_hidden = False

    # 创建 commit 列表
    commit_list = CommitList()

    # 获取 work-in-progress 的 child
    work_in_progress = getattr(root, "current", None)
    if work_in_progress is None:
        work_in_progress = root

    first_fiber = getattr(work_in_progress, "child", None)

    # 第一阶段：Before Mutation（读取 DOM 快照）
    commit_before_mutation_effects(first_fiber, commit_list)

    # 第二阶段：Mutation（应用 DOM 变更）
    commit_mutation_effects(first_fiber, commit_list, root)

    # 第三阶段：Layout Effects（执行布局效果）
    commit_layout_effects(first_fiber, commit_list)

    # 准备被动效果
    passive_effect_state = prepare_passive_effects(first_fiber, commit_list)

    # 准备 root 完成状态
    root_completion_state = {
        "containsSuspendedFibers": getattr(
            root, "contains_suspended_fibers", False
        ),
    }

    # 创建 PreparedCommit
    prepared = PreparedCommit(
        work_root=root,
        commit_list=commit_list,
        root_completion_state=root_completion_state,
        passive_effect_state=passive_effect_state,
    )

    return prepared


# =============================================================================
# 第一阶段：Before Mutation
# =============================================================================


def commit_before_mutation_effects(
    first_fiber: Optional[Any], commit_list: CommitList
) -> None:
    """
    Before Mutation 阶段

    在此阶段读取 DOM 快照，用于 getSnapshotBeforeUpdate。
    """
    fiber = first_fiber

    while fiber is not None:
        _commit_before_mutation_effect_on_fiber(fiber, commit_list)

        # 遍历子节点
        if getattr(fiber, "child", None) is not None:
            fiber = fiber.child
            continue

        # 遍历 sibling
        if getattr(fiber, "sibling", None) is not None:
            fiber = fiber.sibling
            continue

        # 返回父节点
        while getattr(fiber, "sibling", None) is None:
            fiber = getattr(fiber, "return_fiber", None)
            if fiber is None:
                return
        fiber = fiber.sibling


def _commit_before_mutation_effect_on_fiber(
    fiber: Any, commit_list: CommitList
) -> None:
    """
    在单个 Fiber 上执行 Before Mutation 效果
    """
    flags = getattr(fiber, "flags", NoFlags)
    work_tag = getattr(fiber, "tag", 0)

    # 检查是否有 Snapshot 标志（getSnapshotBeforeUpdate）
    if (flags & Snapshot) != NoFlags:
        if work_tag == ClassComponent:
            # TODO: 调用 getSnapshotBeforeUpdate
            pass

    # 检查子树是否有 BeforeMutation 效果
    subtree_flags = getattr(fiber, "subtree_flags", NoFlags)
    if (subtree_flags & MutationMask) == NoFlags:
        return


# =============================================================================
# 第二阶段：Mutation
# =============================================================================


def commit_mutation_effects(
    first_fiber: Optional[Any], commit_list: CommitList, root: Any
) -> None:
    """
    Mutation 阶段

    应用所有 DOM 变更。这是实际修改 DOM 的阶段。
    """
    fiber = first_fiber

    while fiber is not None:
        _commit_mutation_effect_on_fiber(fiber, commit_list, root)

        # 遍历子节点
        if getattr(fiber, "child", None) is not None:
            fiber = fiber.child
            continue

        # 遍历 sibling
        if getattr(fiber, "sibling", None) is not None:
            fiber = fiber.sibling
            continue

        # 返回父节点
        while getattr(fiber, "sibling", None) is None:
            fiber = getattr(fiber, "return_fiber", None)
            if fiber is None:
                return
        fiber = fiber.sibling

    # 处理所有的 DOM 变更
    _apply_all_dom_changes(commit_list, root)


def _commit_mutation_effect_on_fiber(
    fiber: Any, commit_list: CommitList, root: Any
) -> None:
    """
    在单个 Fiber 上执行 Mutation 效果
    """
    flags = getattr(fiber, "flags", NoFlags)
    work_tag = getattr(fiber, "tag", 0)

    # 根据标志收集效果
    if (flags & Placement) != NoFlags:
        commit_list.placements.append(fiber)

    if (flags & Update) != NoFlags:
        commit_list.updates.append(fiber)

    if (flags & ChildDeletion) != NoFlags:
        # 收集需要删除的子节点
        deletions = getattr(fiber, "deletions", None)
        if deletions is not None:
            commit_list.deletions.extend(deletions)

    if (flags & ContentReset) != NoFlags:
        commit_list.content_resets.append(fiber)

    if (flags & Ref) != NoFlags:
        commit_list.ref_callbacks.append(fiber)

    # 检查子树是否有 Mutation 效果
    subtree_flags = getattr(fiber, "subtree_flags", NoFlags)
    if (subtree_flags & MutationMask) == NoFlags:
        return


def _apply_all_dom_changes(commit_list: CommitList, root: Any) -> None:
    """
    应用所有的 DOM 变更

    按照正确的顺序执行：
    1. 删除节点（先删除，避免影响其他操作）
    2. 更新节点
    3. 放置节点（最后放置，因为新节点可能影响布局）
    """
    from pyinkcli.dom import (
        appendChildNode,
        insertBeforeNode,
        removeChildNode,
        setAttribute,
        setTextNodeValue,
    )

    # 1. 删除节点
    for fiber in commit_list.deletions:
        _commit_deletion(fiber)

    # 2. 更新节点
    for fiber in commit_list.updates:
        _commit_update(fiber)

    # 3. 重置内容
    for fiber in commit_list.content_resets:
        _commit_content_reset(fiber)

    # 4. 放置节点
    for fiber in commit_list.placements:
        _commit_placement(fiber, root)

    # 5. 执行 Ref 回调
    for fiber in commit_list.ref_callbacks:
        _commit_ref(fiber)


def _commit_deletion(fiber: Any) -> None:
    """
    提交删除操作
    """
    parent = getattr(fiber, "return_fiber", None)
    if parent is None:
        return

    parent_node = getattr(parent, "state_node", None)
    if parent_node is None:
        return

    child_node = getattr(fiber, "state_node", None)
    if child_node is not None:
        try:
            removeChildNode(parent_node, child_node)
        except Exception:
            pass  # 节点可能已经被删除


def _commit_update(fiber: Any) -> None:
    """
    提交更新操作
    """
    from ..dom import setAttribute, setStyle

    instance = getattr(fiber, "state_node", None)
    if instance is None:
        return

    work_tag = getattr(fiber, "tag", 0)

    if work_tag == HostComponent:
        # 更新属性
        pending_props = getattr(fiber, "memoized_props", {})
        alternate = getattr(fiber, "alternate", None)
        if alternate is not None:
            old_props = getattr(alternate, "memoized_props", {})

            for key, value in pending_props.items():
                if key == "children" or key == "style":
                    continue
                old_value = old_props.get(key)
                if old_value != value:
                    try:
                        setAttribute(instance, key, value)
                    except Exception:
                        pass

        # 更新样式
        style = pending_props.get("style")
        if style is not None:
            old_style = {}
            if alternate is not None:
                old_style = getattr(alternate, "memoized_props", {}).get("style", {})

            if old_style != style:
                try:
                    setStyle(instance, style)
                except Exception:
                    pass

    elif work_tag == HostText:
        # 更新文本
        text_content = getattr(fiber, "memoized_props", "")
        try:
            setTextNodeValue(instance, text_content)
        except Exception:
            pass


def _commit_content_reset(fiber: Any) -> None:
    """
    提交内容重置操作
    """
    instance = getattr(fiber, "state_node", None)
    if instance is None:
        return

    # 重置文本内容为空
    try:
        setTextNodeValue(instance, "")
    except Exception:
        pass


def _commit_placement(fiber: Any, root: Any) -> None:
    """
    提交放置操作（插入新节点）
    """
    from ..dom import appendChildNode

    instance = getattr(fiber, "state_node", None)
    if instance is None:
        return

    # 查找父节点
    parent = getattr(fiber, "return_fiber", None)
    if parent is None:
        # 可能是 root 的直接子节点
        parent_node = getattr(root, "container", None)
        if parent_node is None:
            parent_node = getattr(root, "state_node", None)
    else:
        parent_node = getattr(parent, "state_node", None)

    if parent_node is not None:
        try:
            appendChildNode(parent_node, instance)
        except Exception:
            pass


def _commit_ref(fiber: Any) -> None:
    """
    提交 Ref 回调
    """
    ref = getattr(fiber, "ref", None)
    if ref is None:
        return

    instance = getattr(fiber, "state_node", None)

    # 调用 Ref 回调
    if callable(ref):
        try:
            ref(instance)
        except Exception:
            pass
    elif hasattr(ref, "current"):
        # React.createRef()
        ref.current = instance


# =============================================================================
# 第三阶段：Layout Effects
# =============================================================================


def commit_layout_effects(first_fiber: Optional[Any], commit_list: CommitList) -> None:
    """
    Layout Effects 阶段

    执行 useLayoutEffect 和 componentDidMount/Update。
    这个阶段是同步的，会阻塞浏览器绘制。
    """
    fiber = first_fiber

    while fiber is not None:
        _commit_layout_effect_on_fiber(fiber, commit_list)

        # 遍历子节点
        if getattr(fiber, "child", None) is not None:
            fiber = fiber.child
            continue

        # 遍历 sibling
        if getattr(fiber, "sibling", None) is not None:
            fiber = fiber.sibling
            continue

        # 返回父节点
        while getattr(fiber, "sibling", None) is None:
            fiber = getattr(fiber, "return_fiber", None)
            if fiber is None:
                return
        fiber = fiber.sibling

    # 执行所有布局效果
    _execute_layout_effects(commit_list)


def _commit_layout_effect_on_fiber(fiber: Any, commit_list: CommitList) -> None:
    """
    在单个 Fiber 上收集 Layout Effects
    """
    flags = getattr(fiber, "flags", NoFlags)
    work_tag = getattr(fiber, "tag", 0)

    # 检查是否有布局效果
    if (flags & LayoutMask) != NoFlags:
        if work_tag in (FunctionComponent, SimpleMemoComponent, ForwardRef):
            # 收集 Hook 布局效果
            _collect_layout_hook_effects(fiber, commit_list)
        elif work_tag == ClassComponent:
            # 收集类组件生命周期
            _collect_class_lifecycle(fiber, commit_list)

    # 检查子树是否有布局效果
    subtree_flags = getattr(fiber, "subtree_flags", NoFlags)
    if (subtree_flags & LayoutMask) == NoFlags:
        return


def _collect_layout_hook_effects(fiber: Any, commit_list: CommitList) -> None:
    """
    收集函数组件的布局 Hook 效果
    """
    update_queue = getattr(fiber, "update_queue", None)
    if update_queue is None:
        return

    last_effect = getattr(update_queue, "last_effect", None)
    if last_effect is None:
        return

    # 遍历效果链表
    current_effect = last_effect.next if hasattr(last_effect, "next") else None

    while current_effect is not None:
        tag = getattr(current_effect, "tag", 0)
        create_fn = getattr(current_effect, "create", None)

        # 检查是否是布局效果 (HookLayout = 4)
        if (tag & 4) != 0 and create_fn is not None:
            commit_list.layout_effects.append(
                {
                    "fiber": fiber,
                    "create": create_fn,
                    "destroy": getattr(current_effect, "inst", {}).get("destroy"),
                    "effect": current_effect,
                }
            )

        # 移动到下一个效果
        if current_effect == last_effect:
            break
        current_effect = getattr(current_effect, "next", None)


def _collect_class_lifecycle(fiber: Any, commit_list: CommitList) -> None:
    """
    收集类组件的生命周期方法
    """
    instance = getattr(fiber, "state_node", None)
    if instance is None:
        return

    alternate = getattr(fiber, "alternate", None)

    if alternate is None:
        # 首次挂载：调用 componentDidMount
        if hasattr(instance, "componentDidMount"):
            commit_list.layout_effects.append(
                {
                    "fiber": fiber,
                    "create": instance.componentDidMount,
                    "type": "class_mount",
                }
            )
    else:
        # 更新：调用 componentDidUpdate
        if hasattr(instance, "componentDidUpdate"):
            prev_props = getattr(alternate, "memoized_props", {})
            prev_state = getattr(alternate, "state", None)
            commit_list.layout_effects.append(
                {
                    "fiber": fiber,
                    "create": lambda: instance.componentDidUpdate(
                        prev_props, prev_state
                    ),
                    "type": "class_update",
                }
            )


def _execute_layout_effects(commit_list: CommitList) -> None:
    """
    执行所有布局效果
    """
    for effect in commit_list.layout_effects:
        create_fn = effect.get("create")
        if create_fn is None:
            continue

        try:
            # 执行创建函数
            cleanup = create_fn()

            # 保存清理函数
            effect_record = effect.get("effect")
            if effect_record is not None:
                inst = getattr(effect_record, "inst", None)
                if inst is not None:
                    inst.destroy = cleanup
        except Exception as e:
            # TODO: 错误处理
            pass


# =============================================================================
# 被动效果处理
# =============================================================================


def prepare_passive_effects(
    first_fiber: Optional[Any], commit_list: CommitList
) -> dict:
    """
    准备被动效果（useEffect）

    被动效果在浏览器绘制后异步执行。
    """
    fiber = first_fiber

    while fiber is not None:
        _collect_passive_effects(fiber, commit_list)

        # 遍历子节点
        if getattr(fiber, "child", None) is not None:
            fiber = fiber.child
            continue

        # 遍历 sibling
        if getattr(fiber, "sibling", None) is not None:
            fiber = fiber.sibling
            continue

        # 返回父节点
        while getattr(fiber, "sibling", None) is None:
            fiber = getattr(fiber, "return_fiber", None)
            if fiber is None:
                return {}
        fiber = fiber.sibling

    return {
        "has_deferred_passive_work": len(commit_list.passive_mount_effects) > 0,
        "pending_passive_mount_effects": len(commit_list.passive_mount_effects),
        "pending_passive_unmount_fibers": len(commit_list.passive_unmount_effects),
    }


def _collect_passive_effects(fiber: Any, commit_list: CommitList) -> None:
    """
    收集被动效果
    """
    flags = getattr(fiber, "flags", NoFlags)
    work_tag = getattr(fiber, "tag", 0)

    # 检查是否有被动效果
    if (flags & Passive) != NoFlags:
        if work_tag in (FunctionComponent, SimpleMemoComponent, ForwardRef):
            _collect_passive_hook_effects(fiber, commit_list)

    # 检查子树是否有被动效果
    subtree_flags = getattr(fiber, "subtree_flags", NoFlags)
    if (subtree_flags & Passive) == NoFlags:
        return


def _collect_passive_hook_effects(fiber: Any, commit_list: CommitList) -> None:
    """
    收集函数组件的被动 Hook 效果
    """
    update_queue = getattr(fiber, "update_queue", None)
    if update_queue is None:
        return

    last_effect = getattr(update_queue, "last_effect", None)
    if last_effect is None:
        return

    # 遍历效果链表
    current_effect = last_effect.next if hasattr(last_effect, "next") else None

    while current_effect is not None:
        tag = getattr(current_effect, "tag", 0)
        create_fn = getattr(current_effect, "create", None)

        # 检查是否是被动效果 (HookPassive = 8)
        if (tag & 8) != 0 and create_fn is not None:
            commit_list.passive_mount_effects.append(
                {
                    "fiber": fiber,
                    "create": create_fn,
                    "destroy": getattr(current_effect, "inst", {}).get("destroy"),
                    "effect": current_effect,
                }
            )

        # 移动到下一个效果
        if current_effect == last_effect:
            break
        current_effect = getattr(current_effect, "next", None)


# =============================================================================
# 运行已准备的提交效果
# =============================================================================


def run_prepared_commit_effects(
    reconciler: Any, container: Any, prepared: PreparedCommit
) -> None:
    """
    运行已准备的提交效果

    这是 commit 阶段的最后一部分，执行所有收集的效果。
    """
    # 更新 root 完成状态
    if prepared.root_completion_state is not None:
        reconciler._last_root_completion_state = prepared.root_completion_state
        reconciler._last_root_commit_suspended = prepared.root_completion_state.get(
            "containsSuspendedFibers",
            False,
        )

    # 执行布局效果
    for effect in prepared.commit_list.layout_effects:
        tag = effect.get("tag") if hasattr(effect, "get") else getattr(effect, "tag", None)
        payload = effect.get("payload", {}) if hasattr(effect, "get") else getattr(effect, "payload", {})
        if tag == "request_render":
            immediate = payload.get("immediate", False)
            if prepared.root_completion_state and prepared.root_completion_state.get(
                "containsSuspendedFibers"
            ):
                immediate = True
            reconciler._host_config.request_render(
                getattr(container, "current_update_priority", 0), immediate
            )
        elif tag == "calculate_layout":
            calculate_layout = getattr(reconciler, "_calculate_layout", None)
            if callable(calculate_layout):
                calculate_layout(getattr(container, "container", container))
        elif (hasattr(effect, "__contains__") and "create" in effect) or hasattr(effect, "create"):
            create_fn = effect["create"] if hasattr(effect, "__getitem__") and not hasattr(effect, "create") else getattr(effect, "create", None)
            if callable(create_fn):
                try:
                    cleanup = create_fn()
                    if hasattr(effect, "__setitem__") and not hasattr(effect, "cleanup"):
                        effect["cleanup"] = cleanup
                    else:
                        setattr(effect, "cleanup", cleanup)
                except Exception:
                    pass


runPreparedCommitEffects = run_prepared_commit_effects


# =============================================================================
# 辅助函数
# =============================================================================


def get_host_parent(fiber: Any, root: Any) -> Optional[Any]:
    """
    获取 Fiber 的宿主父节点

    向上遍历找到最近的有 state_node 的祖先。
    """
    parent = getattr(fiber, "return_fiber", None)

    while parent is not None:
        state_node = getattr(parent, "state_node", None)
        if state_node is not None:
            return state_node
        parent = getattr(parent, "return_fiber", None)

    # 如果找不到，返回 root 的 container
    return getattr(root, "container", None) or getattr(root, "state_node", None)


def schedule_passive_effects(
    callback: Callable[[], None], priority: str = "default"
) -> None:
    """
    调度被动效果

    被动效果在浏览器绘制后异步执行。
    """
    import asyncio
    import threading

    # 使用事件循环调度
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 事件循环正在运行，调度到下一个 tick
            loop.call_soon_threadsafe(callback)
        else:
            # 事件循环未运行，创建新线程
            def run_in_thread():
                asyncio.run(callback())

            thread = threading.Thread(target=run_in_thread)
            thread.start()
    except Exception:
        # 回退到同步执行
        callback()


# =============================================================================
# 导出
# =============================================================================


__all__ = [
    # 数据结构
    "CommitList",
    "PreparedCommit",
    # 主入口
    "commit_root",
    "run_prepared_commit_effects",
    "runPreparedCommitEffects",
    # 各阶段函数
    "commit_before_mutation_effects",
    "commit_mutation_effects",
    "commit_layout_effects",
    "prepare_passive_effects",
    # 辅助函数
    "get_host_parent",
    "schedule_passive_effects",
]
