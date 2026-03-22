"""Context helpers aligned with ReactFiberNewContext responsibilities."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Any

from pyinkcli.hooks import _runtime
import pyinkcli.packages.react_reconciler.ReactCurrentFiber as ReactCurrentFiber

if TYPE_CHECKING:
    from pyinkcli.hooks._runtime import HookFiber
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler


_currently_rendering_fiber_stack: list[Any | None] = []


def _get_observed_fiber() -> Any | None:
    if _currently_rendering_fiber_stack:
        return _currently_rendering_fiber_stack[-1]
    if _runtime._runtime.fiber_stack:
        return _runtime._runtime.fiber_stack[-1]
    return ReactCurrentFiber.current


def _recordContextDependency(fiber: Any, context: Any, value: Any) -> None:
    dependencies = getattr(fiber, "dependencies", None)
    if dependencies is None:
        dependencies = []
        setattr(fiber, "dependencies", dependencies)
    for index, dependency in enumerate(dependencies):
        dependency_context = dependency[0] if isinstance(dependency, tuple) else getattr(dependency, "context", None)
        if dependency_context is context:
            dependencies[index] = (context, value)
            return
    dependencies.append((context, value))


def prepareToReadContext(fiber: Any) -> None:
    _currently_rendering_fiber_stack.append(fiber)
    if fiber is not None:
        setattr(fiber, "dependencies", [])


def finishReadingContext() -> None:
    if _currently_rendering_fiber_stack:
        _currently_rendering_fiber_stack.pop()


def checkIfContextChanged(dependencies: list[tuple[Any, Any]] | None) -> bool:
    if not dependencies:
        return False
    for context, memoized_value in dependencies:
        getter = getattr(context, "get", None)
        current_value = getter() if callable(getter) else getattr(context, "_currentValue", None)
        if current_value != memoized_value:
            return True
    return False


def readContext(context: Any) -> Any:
    getter = getattr(context, "get", None)
    value = getter() if callable(getter) else getattr(context, "_currentValue", None)
    observed_fiber = _get_observed_fiber()
    if observed_fiber is not None:
        _recordContextDependency(observed_fiber, context, value)
    return value


def pushProvider(reconciler: _Reconciler, context: Any, next_value: Any) -> AbstractContextManager[Any]:
    provider = context._provide(next_value)
    provider.__enter__()
    reconciler._context_provider_stack.append(provider)
    return provider


def popProvider(reconciler: _Reconciler, context: Any | None = None) -> None:
    del context
    if not reconciler._context_provider_stack:
        return
    provider = reconciler._context_provider_stack.pop()
    provider.__exit__(None, None, None)


__all__ = [
    "checkIfContextChanged",
    "finishReadingContext",
    "popProvider",
    "prepareToReadContext",
    "pushProvider",
    "readContext",
]
