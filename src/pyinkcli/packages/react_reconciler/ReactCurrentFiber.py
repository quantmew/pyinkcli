"""Current fiber bookkeeping used in development helpers."""

from __future__ import annotations

from collections.abc import Callable

from .ReactSharedInternals import shared_internals

current = None
isRendering = False


def getCurrentFiberOwnerNameInDevOrNull() -> str | None:
    if current is None:
        return None
    return (
        getattr(current, "element_type", None)
        or getattr(current, "displayName", None)
        or getattr(current, "__name__", None)
    )


def runWithFiberInDEV(
    fiber: object | None,
    callback: Callable[..., object],
    *args: object,
) -> object:
    previous = setCurrentFiber(fiber)
    try:
        return callback(*args)
    finally:
        setCurrentFiber(previous)


def resetCurrentFiber() -> None:
    global current, isRendering
    shared_internals.getCurrentStack = None
    isRendering = False
    current = None


def setCurrentFiber(fiber: object | None):
    global current, isRendering
    previous = current
    current = fiber
    owner_name = getCurrentFiberOwnerNameInDevOrNull()
    if owner_name is None:
        shared_internals.getCurrentStack = None
    else:
        shared_internals.getCurrentStack = lambda: f"\n    in {owner_name}"
    isRendering = False
    return previous


def setIsRendering(rendering: bool) -> None:
    global isRendering
    isRendering = rendering


def getIsRendering() -> bool | None:
    return isRendering
