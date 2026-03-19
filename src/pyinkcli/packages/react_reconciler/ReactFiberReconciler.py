"""Top-level reconciler construction helpers aligned with ReactFiberReconciler."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

from pyinkcli.hooks._runtime import (
    _batched_updates_runtime,
    _consume_pending_rerender_priority,
    _discrete_updates_runtime,
)
from pyinkcli.packages.react_dom.host import DOMElement
from pyinkcli.packages.react_reconciler.ReactEventPriorities import UpdatePriority

if TYPE_CHECKING:
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler


_reconciler_instance: Optional["_Reconciler"] = None


def diff(before: Dict[str, Any], after: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if before == after:
        return None
    if not before:
        return after
    changed: Dict[str, Any] = {}
    changed_any = False
    for key in before:
        if key not in after:
            changed[key] = None
            changed_any = True
    for key, value in after.items():
        if before.get(key) != value:
            changed[key] = value
            changed_any = True
    return changed if changed_any else None


def cleanupYogaNode(node: Optional[Any]) -> None:
    if node is None:
        return
    unset = getattr(node, "unset_measure_func", None) or getattr(node, "unsetMeasureFunc", None)
    if callable(unset):
        unset()
    free_recursive = getattr(node, "free_recursive", None) or getattr(node, "freeRecursive", None)
    if callable(free_recursive):
        free_recursive()
        return
    free = getattr(node, "free", None)
    if callable(free):
        free()


def loadPackageJson() -> dict[str, str]:
    package_json = Path(__file__).resolve().parents[2] / "package.json"
    if package_json.exists():
        parsed = json.loads(package_json.read_text())
        return {
            "name": parsed.get("name", "pyinkcli"),
            "version": parsed.get("version", "0.1.0"),
        }
    return {"name": "pyinkcli", "version": "0.1.0"}


packageInfo = loadPackageJson()


def getReconciler(root_node: Optional[DOMElement] = None) -> "_Reconciler":
    global _reconciler_instance
    if _reconciler_instance is None and root_node is not None:
        from pyinkcli.packages.react_reconciler.reconciler import _Reconciler

        _reconciler_instance = _Reconciler(root_node)
    return _reconciler_instance


def createReconciler(root_node: DOMElement) -> "_Reconciler":
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler

    return _Reconciler(root_node)


def batchedUpdates(callback: Callable[[], Any]) -> Any:
    return _batched_updates_runtime(callback)


def discreteUpdates(callback: Callable[[], Any]) -> Any:
    return _discrete_updates_runtime(callback)


def consumePendingRerenderPriority() -> Optional[UpdatePriority]:
    return _consume_pending_rerender_priority()


__all__ = [
    "batchedUpdates",
    "cleanupYogaNode",
    "consumePendingRerenderPriority",
    "createReconciler",
    "diff",
    "discreteUpdates",
    "getReconciler",
    "loadPackageJson",
    "packageInfo",
]
