"""Thenable helpers aligned with ReactFiberThenable responsibilities."""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any

from pyinkcli._suspense_runtime import SuspendSignal


def getThenableDisplayName(value: Any) -> str:
    constructor = getattr(type(value), "__name__", "")
    return constructor or "Thenable"


def getThenableStatus(value: Any) -> str:
    if isinstance(value, (asyncio.Future, concurrent.futures.Future)):
        if not value.done():
            return "pending"
        try:
            value.result()
        except BaseException:
            return "rejected"
        return "fulfilled"
    status = getattr(value, "status", None)
    return status if isinstance(status, str) else "pending"


def getThenableValue(value: Any) -> Any:
    if isinstance(value, (asyncio.Future, concurrent.futures.Future)):
        return value.result()
    return getattr(value, "value", None)


def getThenableReason(value: Any) -> Any:
    if isinstance(value, (asyncio.Future, concurrent.futures.Future)):
        try:
            value.result()
        except BaseException as error:
            return error
        return None
    return getattr(value, "reason", None)


def createSuspendedThenableRecord(error: SuspendSignal) -> list[dict[str, Any]]:
    return [
        {
            "name": "SuspendSignal",
            "awaited": {
                "value": {
                    "resource": {"key": repr(error.key)},
                    "message": str(error),
                }
            },
            "env": None,
            "owner": None,
            "stack": None,
        }
    ]


__all__ = [
    "createSuspendedThenableRecord",
    "getThenableDisplayName",
    "getThenableReason",
    "getThenableStatus",
    "getThenableValue",
]
