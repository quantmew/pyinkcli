"""
React Fiber 节点定义 - 双缓冲树结构

实现 Fiber 的 alternate 双缓冲机制，支持并发渲染。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .ReactFiberFlags import NoFlags, Placement, Update
from .ReactFiberLane import NoLane, NoLanes, mergeLanes
from .ReactWorkTags import ClassComponent, Fragment, HostComponent, HostRoot, HostText, SuspenseComponent


# =============================================================================
# Fiber 节点定义
# =============================================================================


@dataclass
class Fiber:
    """
    Fiber 节点 -  React Fiber 架构的核心数据结构

    双缓冲机制：每个 Fiber 节点都有一个 alternate 引用，指向另一棵树的对应节点。
    - current 树：代表当前已渲染的 UI 状态
    - workInProgress 树：代表正在构建的新 UI 状态

    渲染完成后，两棵树互换角色，实现无锁的双缓冲切换。
    """

    # =============================================================================
    # Fiber 身份标识 (不变字段)
    # =============================================================================

    # Fiber 类型标签 (HostComponent, ClassComponent, etc.)
    tag: int = 0

    # 节点 key (用于列表复用)
    key: Optional[str] = None

    # 组件类型 (函数组件、类组件、Host 组件等)
    element_type: Any = None

    # 组件构造函数 (仅 ClassComponent)
    type: Any = None

    # 状态节点 (StateNode) - 类组件实例、FiberRoot 等
    state_node: Any = None

    # =============================================================================
    # 双缓冲链接 (核心字段)
    # =============================================================================

    # alternate Fiber - 双缓冲的另一棵树
    alternate: Optional["Fiber"] = None

    # =============================================================================
    # 树结构指针 (不变字段)
    # =============================================================================

    # 返回父 Fiber
    return_fiber: Optional["Fiber"] = field(default=None, metadata={"alias": "return"})

    # 第一个子 Fiber
    child: Optional["Fiber"] = None

    # 兄弟 Fiber
    sibling: Optional["Fiber"] = None

    # 索引位置 (在 siblings 中的位置)
    index: int = 0

    # ref 引用
    ref: Any = None

    # =============================================================================
    # 渲染状态 (可变字段，每次渲染会重置)
    # =============================================================================

    # 副作用标志位 (Placement, Update, Deletion, etc.)
    flags: int = NoFlags

    # 副作用子树 (仅 root 指向有待处理的副作用子树)
    subtree_flags: int = NoFlags

    # 第一个副作用 Fiber
    first_effect: Optional["Fiber"] = None

    # 最后一个副作用 Fiber
    last_effect: Optional["Fiber"] = None

    # =============================================================================
    # 优先级相关 (可变字段)
    # =============================================================================

    # 当前 Fiber 的 lanes
    lanes: int = NoLanes

    # 子树的 lanes (所有子节点的 lanes 合并)
    child_lanes: int = NoLanes

    # =============================================================================
    # 工作进度 (可变字段)
    # =============================================================================

    # 完成的工作 (memoized 结果)
    memoized_props: Any = None
    memoized_state: Any = None

    # 更新队列
    update_queue: Any = None

    # 上下文
    memoized_context: Any = None

    # 依赖项
    dependencies: Any = None

    # mode (StrictMode, ConcurrentMode, etc.)
    mode: int = 0

    # =============================================================================
    # 调试信息 (仅 DEV 模式)
    # =============================================================================

    # 调试信息
    _debug_source: Any = None
    _debug_owner: Optional["Fiber"] = None
    _debug_stack: Any = None

    def __post_init__(self):
        # 支持 return 字段 (Python 保留字，使用别名)
        if hasattr(self, "_return"):
            self.return_fiber = self._return

    # ===========================================================================
    # 属性别名 (兼容 React 源码命名)
    # ===========================================================================

    @property
    def return_(self) -> Optional["Fiber"]:
        """return 字段的 getter (Python 保留字)"""
        return self.return_fiber

    @return_.setter
    def return_(self, value: Optional["Fiber"]) -> None:
        """return 字段的 setter"""
        self.return_fiber = value

    # ===========================================================================
    # Fiber 复用逻辑
    # ===========================================================================

    @staticmethod
    def create_work_in_progress(current: "Fiber") -> "Fiber":
        """
        创建或复用 work-in-progress Fiber

        双缓冲核心逻辑:
        1. 如果 current.alternate 存在，复用并重置状态
        2. 如果不存在，创建新的 Fiber 并建立 alternate 链接

        Args:
            current: 当前树上的 Fiber 节点

        Returns:
            work-in-progress Fiber 节点
        """
        # 检查是否有可复用的 alternate
        if current.alternate is not None:
            work_in_progress = current.alternate
            # 重置状态
            work_in_progress.flags = NoFlags
            work_in_progress.subtree_flags = NoFlags
            work_in_progress.first_effect = None
            work_in_progress.last_effect = None
            work_in_progress.lanes = NoLanes
            work_in_progress.child_lanes = NoLanes
        else:
            # 创建新的 Fiber
            work_in_progress = Fiber(
                tag=current.tag,
                key=current.key,
                element_type=current.element_type,
                type=current.type,
                state_node=current.state_node,
                memoized_props=current.memoized_props,
                memoized_state=current.memoized_state,
                update_queue=current.update_queue,
                mode=current.mode,
            )
            # 建立双缓冲链接
            work_in_progress.alternate = current
            current.alternate = work_in_progress

        # 复制树结构指针
        work_in_progress.return_fiber = current.return_fiber
        work_in_progress.child = current.child
        work_in_progress.sibling = current.sibling
        work_in_progress.index = current.index
        work_in_progress.ref = current.ref

        # 复制调试信息
        work_in_progress._debug_source = current._debug_source
        work_in_progress._debug_owner = current._debug_owner
        work_in_progress._debug_stack = current._debug_stack

        return work_in_progress

    @staticmethod
    def create_from_template(
        template: Any,
        tag: int,
        key: Optional[str],
        element_type: Any,
        mode: int = 0,
    ) -> "Fiber":
        """
        从模板创建新的 Fiber 节点

        Args:
            template: 可选的模板 Fiber，用于复制属性
            tag: Fiber 类型标签
            key: 节点 key
            element_type: 元素类型
            mode: 渲染模式

        Returns:
            新创建的 Fiber 节点
        """
        fiber = Fiber(
            tag=tag,
            key=key,
            element_type=element_type,
            mode=mode,
        )

        if template is not None:
            # 从模板复制属性
            fiber.memoized_props = getattr(template, "memoized_props", None)
            fiber.memoized_state = getattr(template, "memoized_state", None)
            fiber.update_queue = getattr(template, "update_queue", None)

        return fiber

    # ===========================================================================
    # 辅助方法
    # ===========================================================================

    def reset_lanes(self) -> None:
        """重置优先级相关字段"""
        self.lanes = NoLanes
        self.child_lanes = NoLanes

    def reset_effects(self) -> None:
        """重置副作用相关字段"""
        self.flags = NoFlags
        self.subtree_flags = NoFlags
        self.first_effect = None
        self.last_effect = None

    def mark_update(self) -> None:
        """标记为需要更新"""
        self.flags |= Update

    def mark_placement(self) -> None:
        """标记为需要放置"""
        self.flags |= Placement

    def has_flag(self, flag: int) -> bool:
        """检查是否包含指定的副作用标志"""
        return (self.flags & flag) != NoFlags

    def merge_child_lanes(self, child_lanes: int) -> None:
        """合并子节点的 lanes"""
        self.child_lanes = mergeLanes(self.child_lanes, child_lanes)

    # ===========================================================================
    # 调试支持
    # ===========================================================================

    def debug_info(self) -> str:
        """返回调试信息"""
        tag_names = {
            HostRoot: "HostRoot",
            HostComponent: "HostComponent",
            HostText: "HostText",
            ClassComponent: "ClassComponent",
            Fragment: "Fragment",
            SuspenseComponent: "SuspenseComponent",
        }
        tag_name = tag_names.get(self.tag, f"Unknown({self.tag})")
        element_name = getattr(self.element_type, "__name__", str(self.element_type))
        return f"Fiber({tag_name}, {element_name}, key={self.key}, flags={bin(self.flags)})"


# =============================================================================
# Fiber 工厂函数
# =============================================================================


def create_host_root_fiber(
    container_info: Any = None,
    mode: int = 0,
) -> Fiber:
    """
    创建 Host Root Fiber

    Args:
        container_info: 容器信息
        mode: 渲染模式

    Returns:
        Host Root Fiber 节点
    """
    root_fiber = Fiber(
        tag=HostRoot,
        element_type=None,
        mode=mode,
    )
    return root_fiber


def create_fiber_from_element(
    element: Any,
    mode: int,
    ref: Any = None,
) -> Fiber:
    """
    从 React Element 创建 Fiber

    Args:
        element: React Element
        mode: 渲染模式
        ref: 引用

    Returns:
        Fiber 节点
    """
    # 确定 Fiber 类型
    element_type = getattr(element, "type", element)

    if isinstance(element_type, str):
        # Host 组件
        tag = HostComponent
    elif element_type is Fragment:
        tag = Fragment
    elif isinstance(element_type, type):
        # 类组件
        tag = ClassComponent
    else:
        # 函数组件
        tag = ClassComponent

    fiber = Fiber(
        tag=tag,
        key=getattr(element, "key", None),
        element_type=element_type,
        type=element_type,
        ref=ref,
        mode=mode,
    )

    # 复制 props
    fiber.memoized_props = getattr(element, "props", None)

    return fiber


# =============================================================================
# 导出
# =============================================================================


__all__ = [
    "Fiber",
    "create_host_root_fiber",
    "create_fiber_from_element",
]
