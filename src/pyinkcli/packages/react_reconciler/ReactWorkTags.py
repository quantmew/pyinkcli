"""
React Work Tags - 组件类型标签定义

用于标识 Fiber 节点的类型。
"""

from __future__ import annotations

# =============================================================================
# 基础组件类型
# =============================================================================

# 函数组件
FunctionComponent = 0

# Class 组件
ClassComponent = 1

# Fragment 组件
Fragment = 2

# 原生组件（如 div、span 等）
HostComponent = 3

# Root 组件（应用的根容器）
HostRoot = 4

# 文本节点
HostText = 5

# Portal 组件（用于渲染到子树外）
HostPortal = 6

# =============================================================================
# React 特性组件类型
# =============================================================================

# Suspense 组件
SuspenseComponent = 6

# Context Provider
ContextProvider = 7

# Context Consumer
ContextConsumer = 8

# ForwardRef 组件
ForwardRef = 9

# Profile 组件
Profiler = 10

# 严格模式/并发模式等 Mode 组件
Mode = 11

# =============================================================================
# 优化组件类型
# =============================================================================

# Memo 组件（React.memo 包装的组件）
MemoComponent = 12

# SimpleMemo 组件（内部使用的简化 Memo）
SimpleMemoComponent = 13

# Offscreen 组件（用于隐藏可见子树）
OffscreenComponent = 14

# LegacyHidden 组件
LegacyHiddenComponent = 15

# =============================================================================
# Suspense 相关
# =============================================================================

# SuspenseList 组件
SuspenseListComponent = 16

# Activity 组件（Suspense 的变体）
ActivityComponent = 17

# =============================================================================
# 其他组件类型
# =============================================================================

# Lazy 组件
LazyComponent = 18

# IncompleteClassComponent
IncompleteClassComponent = 19

# ScopeComponent (React Server Components)
ScopeComponent = 20

# TracingMarkerComponent
TracingMarkerComponent = 21

# =============================================================================
# 辅助函数
# =============================================================================


def isFunctionComponent(workTag: int) -> bool:
    """检查是否是函数组件类型"""
    return workTag in (FunctionComponent, SimpleMemoComponent, MemoComponent, ForwardRef)


def isClassComponent(workTag: int) -> bool:
    """检查是否是 Class 组件"""
    return workTag == ClassComponent


def isHostComponent(workTag: int) -> bool:
    """检查是否是原生组件"""
    return workTag == HostComponent


def isHostText(workTag: int) -> bool:
    """检查是否是文本节点"""
    return workTag == HostText


def isSuspenseComponent(workTag: int) -> bool:
    """检查是否是 Suspense 组件"""
    return workTag == SuspenseComponent


def isContextProvider(workTag: int) -> bool:
    """检查是否是 Context Provider"""
    return workTag == ContextProvider


def isContextConsumer(workTag: int) -> bool:
    """检查是否是 Context Consumer"""
    return workTag == ContextConsumer


def isOffscreenComponent(workTag: int) -> bool:
    """检查是否是 Offscreen 组件"""
    return workTag == OffscreenComponent


def isLegacyHiddenComponent(workTag: int) -> bool:
    """检查是否是 LegacyHidden 组件"""
    return workTag == LegacyHiddenComponent


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    # 基础组件
    "FunctionComponent",
    "ClassComponent",
    "Fragment",
    "HostComponent",
    "HostRoot",
    "HostText",
    # React 特性组件
    "SuspenseComponent",
    "ContextProvider",
    "ContextConsumer",
    "ForwardRef",
    "Profiler",
    "Mode",
    # 优化组件
    "MemoComponent",
    "SimpleMemoComponent",
    "OffscreenComponent",
    "LegacyHiddenComponent",
    # Suspense 相关
    "SuspenseListComponent",
    "ActivityComponent",
    # 其他
    "LazyComponent",
    "IncompleteClassComponent",
    "ScopeComponent",
    "TracingMarkerComponent",
    # 辅助函数
    "isFunctionComponent",
    "isClassComponent",
    "isHostComponent",
    "isHostText",
    "isSuspenseComponent",
    "isContextProvider",
    "isContextConsumer",
    "isOffscreenComponent",
    "isLegacyHiddenComponent",
]
