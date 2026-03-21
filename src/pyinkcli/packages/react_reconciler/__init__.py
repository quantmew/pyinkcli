"""React reconciler-aligned namespace for pyinkcli internals."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "ReconcilerContainer",
    "ReconcilerHostConfig",
    "UpdatePriority",
    "batchedUpdates",
    "createReconciler",
    "discreteUpdates",
    "flushScheduledUpdates",
    "flushSyncFromReconciler",
    "getReconciler",
    "packageInfo",
]


def __getattr__(name: str) -> Any:
    if name == "ReconcilerHostConfig":
        from pyinkcli.packages.ink.host_config import ReconcilerHostConfig

        return ReconcilerHostConfig
    if name == "UpdatePriority":
        from pyinkcli.packages.react_reconciler.ReactEventPriorities import UpdatePriority

        return UpdatePriority
    if name == "ReconcilerContainer":
        from pyinkcli.packages.react_reconciler.ReactFiberRoot import ReconcilerContainer

        return ReconcilerContainer
    if name in {
        "batchedUpdates",
        "createReconciler",
        "discreteUpdates",
        "flushScheduledUpdates",
        "flushSyncFromReconciler",
        "getReconciler",
        "packageInfo",
    }:
        module = import_module("pyinkcli.packages.react_reconciler.ReactFiberReconciler")
        return getattr(module, name)
    raise AttributeError(name)
