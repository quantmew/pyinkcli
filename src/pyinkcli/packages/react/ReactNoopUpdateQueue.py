"""No-op update queue aligned with ReactNoopUpdateQueue."""

from __future__ import annotations

from typing import Any


def _warn_noop(_public_instance: Any, _caller_name: str) -> None:
    return None


class _ReactNoopUpdateQueue:
    @staticmethod
    def isMounted(_public_instance: Any) -> bool:
        return False

    @staticmethod
    def enqueueForceUpdate(publicInstance: Any, callback: Any = None, callerName: str | None = None) -> None:
        del callback, callerName
        _warn_noop(publicInstance, "forceUpdate")

    @staticmethod
    def enqueueReplaceState(
        publicInstance: Any,
        completeState: Any,
        callback: Any = None,
        callerName: str | None = None,
    ) -> None:
        del completeState, callback, callerName
        _warn_noop(publicInstance, "replaceState")

    @staticmethod
    def enqueueSetState(
        publicInstance: Any,
        partialState: Any,
        callback: Any = None,
        callerName: str | None = None,
    ) -> None:
        del partialState, callback, callerName
        _warn_noop(publicInstance, "setState")


ReactNoopUpdateQueue = _ReactNoopUpdateQueue()

__all__ = ["ReactNoopUpdateQueue"]
