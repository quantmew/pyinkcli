"""Exception helpers aligned with ReactFiberThrow responsibilities."""

from __future__ import annotations

from typing import Any

from pyinkcli._suspense_runtime import SuspendSignal
from pyinkcli.packages.react_reconciler.ReactFiberThenable import (
    createSuspendedThenableRecord,
)


def isSuspenseException(error: BaseException) -> bool:
    return isinstance(error, SuspendSignal)


def isWorkYieldException(error: BaseException) -> bool:
    from pyinkcli.packages.react_reconciler.ReactChildFiber import WorkYield

    return isinstance(error, WorkYield)


def isControlFlowException(error: BaseException) -> bool:
    return isSuspenseException(error) or isWorkYieldException(error)


def describeThrownValue(error: BaseException) -> list[dict[str, Any]] | None:
    if isinstance(error, SuspendSignal):
        return createSuspendedThenableRecord(error)
    return None


__all__ = [
    "describeThrownValue",
    "isControlFlowException",
    "isSuspenseException",
    "isWorkYieldException",
]
