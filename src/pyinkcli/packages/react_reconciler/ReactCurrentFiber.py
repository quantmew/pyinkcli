from __future__ import annotations

from .ReactSharedInternals import shared_internals

current = None
_is_rendering = False


def setCurrentFiber(fiber) -> None:
    global current
    current = fiber


def setIsRendering(value: bool) -> None:
    global _is_rendering
    _is_rendering = value
    if value and current is not None:
        shared_internals.getCurrentStack = lambda: f"at {getattr(current, 'element_type', '')}"
    elif not value:
        shared_internals.getCurrentStack = None


def resetCurrentFiber() -> None:
    global current, _is_rendering
    current = None
    _is_rendering = False
    shared_internals.getCurrentStack = None


def runWithFiberInDEV(fiber, callback):
    previous = current
    setCurrentFiber(fiber)
    try:
        return callback()
    finally:
        setCurrentFiber(previous)


def getCurrentFiberOwnerNameInDevOrNull():
    return getattr(current, "element_type", None)

