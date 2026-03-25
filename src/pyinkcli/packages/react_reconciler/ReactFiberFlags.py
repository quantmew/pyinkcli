"""
React Fiber Flags - 副作用标志位定义

用于标记 Fiber 节点需要执行的副作用操作。
"""

from __future__ import annotations

# =============================================================================
# 副作用标志 (Flags)
# =============================================================================

# 无副作用
NoFlags = 0b00000000000000000000000000000000

# 表示 Fiber 已经被处理过（用于标记已执行的工作）
PerformedWork = 1 << 0

# 表示 Fiber 需要被创建或更新
Update = 1 << 1

# 表示 Fiber 需要被放置到 DOM 中 (插入)
Placement = 1 << 2

# 表示 Fiber 需要被删除
Deletion = 1 << 3

# 表示 Fiber 的内容需要更新 (仅 HostText)
ContentReset = 1 << 4

# 表示 Fiber 的 callback 需要被执行
Callback = 1 << 5

# 表示 Ref 需要被更新
Ref = 1 << 6

# 表示 Ref 需要被清理 (仅 ClassComponent)
Snapshot = 1 << 7

# 表示子树需要被动效果 (仅 HostRoot, ClassComponent)
Passive = 1 << 8

# 表示子树有副作用 (用于优化遍历)
HasEffects = 1 << 9

# 表示生命周期需要被更新
UpdateLifeCycle = 1 << 10

# 表示 Fiber 有 snapshot
HasSnapshot = 1 << 11

# 表示 Fiber 有副作用
AlwaysShouldBeClaimed = 1 << 12

# 表示 Suspense 边界需要重新显示
DidCapture = 1 << 13

# 表示需要捕获错误（错误边界/Suspense）
ShouldCapture = 1 << 13

# 表示 Fiber 未完成渲染（错误、suspended 等情况）
Incomplete = 1 << 14

# 表示 Ref 需要被清理
InEffect = Ref

# =============================================================================
# React 18 新增标志
# =============================================================================

# 表示需要插入或更新子节点（与 Deletion 不同的概念）
ChildDeletion = 1 << 15

# 表示需要强制重新计算布局
ForceUpdateForLegacySubtree = 1 << 16

# 表示需要强制更新 Legacy Suspense (用于 Suspense 的旧版本兼容)
ForceUpdateForLegacySuspense = 1 << 17

# 表示需要强制客户端渲染（用于 Suspense fallback）
ForceClientRender = 1 << 18

# 表示正在水合（hydration）
Hydrating = 1 << 19

# 表示提交可能会被挂起
MaySuspendCommit = 1 << 20

# 表示提交应该被挂起
ShouldSuspendCommit = 1 << 21

# 表示静态掩码（用于 bailout 优化）
StaticMask = 1 << 22

# 表示可见性变化（用于 Offscreen/Visibility）
Visibility = 1 << 23

# 表示需要更新 React Offscreen 组件
OffscreenRef = 1 << 24

# 表示 Suspense 边界已捕获错误（与 DidCapture 相同）
SuspenseDidCapture = DidCapture

# 表示需要执行 passive destroy
PassiveDestroy = 1 << 25

# 表示需要执行 passive unmount
PassiveUnmount = 1 << 26

# 表示需要执行 passive update
PassiveUpdate = 1 << 27

# =============================================================================
# 组合标志（ masks ）
# =============================================================================

# 布局效果掩码
LayoutMask = Update | Callback | Ref | HasSnapshot

# 变异效果掩码
MutationMask = Placement | Update | Deletion | ContentReset | Ref

# 被动效果掩码
PassiveMask = Passive | PassiveUpdate

# 所有可能触发 bailout 的静态标志
StaticMask = OffscreenRef

# 所有副作用标志 (用于检查是否有任何副作用)
AllEffects = (
    Update
    | Placement
    | Deletion
    | ContentReset
    | Callback
    | Ref
    | Snapshot
    | Passive
    | HasEffects
    | UpdateLifeCycle
    | HasSnapshot
    | AlwaysShouldBeClaimed
    | DidCapture
    | ChildDeletion
    | ForceUpdateForLegacySubtree
    | ForceUpdateForLegacySuspense
    | ForceClientRender
    | Hydrating
    | MaySuspendCommit
    | ShouldSuspendCommit
    | Visibility
    | OffscreenRef
    | SuspenseDidCapture
    | PassiveDestroy
    | PassiveUnmount
    | PassiveUpdate
)

# 布局阶段需要处理的副作用
LayoutEffects = (
    Update
    | Ref
    | Snapshot
    | Callback
)

# 提交阶段需要处理的副作用
CommitEffects = (
    Placement
    | Update
    | Deletion
    | ContentReset
    | Ref
)

# =============================================================================
# 子树标志 (SubtreeFlags)
# =============================================================================

# 子树需要被动效果
HasPassiveEffects = 1 << 18

# 子树有任何副作用
HasUpdate = 1 << 19

# 子树有快照
HasSnapshotSubtree = 1 << 20

# 子树需要布局效果
HasLayoutEffects = 1 << 21

# =============================================================================
# Hook 标志
# =============================================================================

# Hook 需要重新执行
HookHasEffect = 1 << 0

# Hook 需要被动清理
HookPassive = 1 << 1

# Hook 需要被动清理 (已挂载)
HookHasPassiveEffect = 1 << 2

# Hook 需要布局清理
HookHasLayoutEffect = 1 << 3

# =============================================================================
# 辅助函数
# =============================================================================


def includesUpdate(flags: int) -> bool:
    """检查是否包含 Update 标志"""
    return (flags & Update) != NoFlags


def includesPlacement(flags: int) -> bool:
    """检查是否包含 Placement 标志"""
    return (flags & Placement) != NoFlags


def includesDeletion(flags: int) -> bool:
    """检查是否包含 Deletion 标志"""
    return (flags & Deletion) != NoFlags


def includesRef(flags: int) -> bool:
    """检查是否包含 Ref 标志"""
    return (flags & Ref) != NoFlags


def includesPassive(flags: int) -> bool:
    """检查是否包含 Passive 标志"""
    return (flags & Passive) != NoFlags


def includesDidCapture(flags: int) -> bool:
    """检查是否包含 DidCapture 标志 (Suspense 已捕获)"""
    return (flags & DidCapture) != NoFlags


def includesIncomplete(flags: int) -> bool:
    """检查是否包含 Incomplete 标志 (Fiber 未完成)"""
    return (flags & Incomplete) != NoFlags


def includesAnyEffects(flags: int) -> bool:
    """检查是否包含任何副作用"""
    return (flags & AllEffects) != NoFlags


def mergeFlags(a: int, b: int) -> int:
    """合并两个 flags"""
    return a | b


def removeFlags(flags: int, to_remove: int) -> int:
    """从 flags 中移除指定的标志"""
    return flags & ~to_remove


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    # 常量
    "NoFlags",
    "PerformedWork",
    "Update",
    "Placement",
    "Deletion",
    "ContentReset",
    "Callback",
    "Ref",
    "Snapshot",
    "Passive",
    "HasEffects",
    "UpdateLifeCycle",
    "HasSnapshot",
    "AlwaysShouldBeClaimed",
    "DidCapture",
    "ShouldCapture",
    "Incomplete",
    "ChildDeletion",
    "ForceUpdateForLegacySubtree",
    "ForceUpdateForLegacySuspense",
    "ForceClientRender",
    "Hydrating",
    "MaySuspendCommit",
    "ShouldSuspendCommit",
    "StaticMask",
    "Visibility",
    "OffscreenRef",
    "SuspenseDidCapture",
    "PassiveDestroy",
    "PassiveUnmount",
    "PassiveUpdate",
    # 组合
    "AllEffects",
    "LayoutEffects",
    "CommitEffects",
    "LayoutMask",
    "MutationMask",
    "PassiveMask",
    # 子树标志
    "HasPassiveEffects",
    "HasUpdate",
    "HasSnapshotSubtree",
    "HasLayoutEffects",
    # Hook 标志
    "HookHasEffect",
    "HookPassive",
    "HookHasPassiveEffect",
    "HookHasLayoutEffect",
    # 辅助函数
    "includesUpdate",
    "includesPlacement",
    "includesDeletion",
    "includesRef",
    "includesPassive",
    "includesDidCapture",
    "includesIncomplete",
    "includesAnyEffects",
    "mergeFlags",
    "removeFlags",
]
