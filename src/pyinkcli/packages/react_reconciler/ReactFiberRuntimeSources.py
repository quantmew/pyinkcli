"""Runtime source dependency tracking for reconciler bailout decisions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyinkcli.packages.react_reconciler.ReactEventPriorities import DefaultEventPriority
from pyinkcli.packages.react_reconciler.ReactFiberConcurrentUpdates import (
    markFiberUpdated,
    unsafe_markUpdateLaneFromFiberToRoot,
)

if TYPE_CHECKING:
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler


def initializeRuntimeSourceVersions(reconciler: _Reconciler) -> None:
    reconciler._runtime_source_versions = {}


def getRuntimeSourceVersion(reconciler: _Reconciler, source: str) -> int:
    versions = getattr(reconciler, "_runtime_source_versions", None)
    if not isinstance(versions, dict):
        reconciler._runtime_source_versions = {}
        versions = reconciler._runtime_source_versions
    return int(versions.get(source, 0))


def recordRuntimeSourceDependency(
    reconciler: _Reconciler | None,
    fiber: Any,
    source: str,
) -> None:
    if reconciler is None or fiber is None:
        return
    current_version = getRuntimeSourceVersion(reconciler, source)
    dependencies = getattr(fiber, "runtime_source_deps", None)
    if dependencies is None:
        dependencies = []
        setattr(fiber, "runtime_source_deps", dependencies)
    for index, dependency in enumerate(dependencies):
        if dependency[0] == source:
            dependencies[index] = (source, current_version)
            return
    dependencies.append((source, current_version))


def checkIfRuntimeSourcesChanged(
    reconciler: _Reconciler | None,
    dependencies: list[tuple[str, int]] | None,
) -> bool:
    if reconciler is None or not dependencies:
        return False
    for source, version in dependencies:
        if getRuntimeSourceVersion(reconciler, source) != version:
            return True
    return False


def markRuntimeSourceUpdated(
    reconciler: _Reconciler | None,
    source: str,
    *,
    fiber: Any | None = None,
    lane: int = DefaultEventPriority,
) -> None:
    if reconciler is None:
        return
    current_version = getRuntimeSourceVersion(reconciler, source)
    reconciler._runtime_source_versions[source] = current_version + 1
    if fiber is not None:
        markFiberUpdated(fiber, lane)
        unsafe_markUpdateLaneFromFiberToRoot(fiber, lane)


__all__ = [
    "checkIfRuntimeSourcesChanged",
    "getRuntimeSourceVersion",
    "initializeRuntimeSourceVersions",
    "markRuntimeSourceUpdated",
    "recordRuntimeSourceDependency",
]
