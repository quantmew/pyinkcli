"""Runtime source dependency bookkeeping."""

from __future__ import annotations

from typing import Any

from .ReactEventPriorities import DefaultEventPriority


def recordRuntimeSourceDependency(
    reconciler: Any | None,
    fiber: Any | None,
    source: str,
) -> None:
    if reconciler is None or fiber is None:
        return

    dependencies = getattr(reconciler, "_runtime_source_dependencies", None)
    if dependencies is None:
        dependencies = {}
        reconciler._runtime_source_dependencies = dependencies

    dependencies.setdefault(source, set()).add(getattr(fiber, "component_id", id(fiber)))

    fiber_sources = getattr(fiber, "runtime_source_deps", None)
    if fiber_sources is not None:
        fiber_sources.append((source, len(fiber_sources)))


def markRuntimeSourceUpdated(reconciler: Any | None, source: str) -> None:
    if reconciler is None or source == "imperative_render":
        return

    updated_sources = getattr(reconciler, "_updated_runtime_sources", None)
    if updated_sources is None:
        updated_sources = set()
        reconciler._updated_runtime_sources = updated_sources
    updated_sources.add(source)

    dependencies = getattr(reconciler, "_runtime_source_dependencies", None)
    if not dependencies or source not in dependencies:
        return

    from .dispatcher import requestRerender

    if source in dependencies:
        requestRerender(priority=DefaultEventPriority)


__all__ = ["recordRuntimeSourceDependency", "markRuntimeSourceUpdated"]
