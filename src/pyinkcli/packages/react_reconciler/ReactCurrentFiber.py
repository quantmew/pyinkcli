"""Current fiber tracking aligned with ReactCurrentFiber responsibilities."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pyinkcli.packages.react_reconciler.ReactSharedInternals import shared_internals

current: Any | None = None
isRendering: bool = False


def getCurrentFiberOwnerNameInDevOrNull() -> str | None:
    fiber = current
    if fiber is None:
        return None
    return getattr(fiber, "element_type", None) or getattr(fiber, "component_id", None)


def getCurrentFiberStackInDev() -> str:
    fiber = current
    if fiber is None:
        return ""
    display_name = getattr(fiber, "element_type", None) or getattr(fiber, "component_id", "Unknown")
    return f"\n    in {display_name}"


def runWithFiberInDEV(
    fiber: Any | None,
    callback: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    previous_fiber = current
    setCurrentFiber(fiber)
    try:
        return callback(*args, **kwargs)
    finally:
        setCurrentFiber(previous_fiber)


def resetCurrentFiber() -> None:
    global current, isRendering
    shared_internals.getCurrentStack = None
    isRendering = False
    current = None


def setCurrentFiber(fiber: Any | None) -> None:
    global current, isRendering
    current = fiber
    isRendering = False
    shared_internals.getCurrentStack = None if fiber is None else getCurrentFiberStackInDev


def setIsRendering(rendering: bool) -> None:
    global isRendering
    isRendering = rendering


def getIsRendering() -> bool:
    return isRendering


__all__ = [
    "current",
    "getCurrentFiberOwnerNameInDevOrNull",
    "getCurrentFiberStackInDev",
    "getIsRendering",
    "isRendering",
    "resetCurrentFiber",
    "runWithFiberInDEV",
    "setCurrentFiber",
    "setIsRendering",
]
