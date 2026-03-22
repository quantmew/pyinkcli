"""Minimal legacy context helpers."""

from __future__ import annotations

from typing import Any

emptyContextObject: dict[str, Any] = {}
_provider_stack: list[tuple[Any, Any]] = []
_current_reader: Any = None


def findCurrentUnmaskedContext(_fiber: Any) -> dict[str, Any]:
    return emptyContextObject


def processChildContext(_fiber: Any, _component: Any, parent_context: dict[str, Any]) -> dict[str, Any]:
    return parent_context


def isContextProvider(component: Any) -> bool:
    return bool(getattr(component, "childContextTypes", None))


def pushProvider(_reconciler: Any, context: Any, value: Any) -> None:
    previous = getattr(context, "_currentValue", getattr(context, "_current_value", None))
    _provider_stack.append((context, previous))
    if hasattr(context, "_currentValue"):
        context._currentValue = value
    if hasattr(context, "_currentValue2"):
        context._currentValue2 = value
    if hasattr(context, "_current_value"):
        context._current_value = value


def popProvider(_reconciler: Any, context: Any) -> None:
    if not _provider_stack:
        return
    previous_context, previous_value = _provider_stack.pop()
    if previous_context is not context:
        context = previous_context
    if hasattr(context, "_currentValue"):
        context._currentValue = previous_value
    if hasattr(context, "_currentValue2"):
        context._currentValue2 = previous_value
    if hasattr(context, "_current_value"):
        context._current_value = previous_value


def prepareToReadContext(fiber: Any) -> None:
    global _current_reader
    _current_reader = fiber
    fiber.dependencies = []


def finishReadingContext() -> None:
    global _current_reader
    _current_reader = None


def readContext(context: Any) -> Any:
    value = getattr(context, "_currentValue", getattr(context, "_current_value", getattr(context, "_default_value", None)))
    if _current_reader is not None:
        _current_reader.dependencies.append((context, value))
    return value


def checkIfContextChanged(dependencies: list[tuple[Any, Any]]) -> bool:
    for context, previous_value in dependencies:
        current_value = getattr(context, "_currentValue", getattr(context, "_current_value", getattr(context, "_default_value", None)))
        if current_value != previous_value:
            return True
    return False


__all__ = [
    "emptyContextObject",
    "findCurrentUnmaskedContext",
    "processChildContext",
    "isContextProvider",
    "pushProvider",
    "popProvider",
    "prepareToReadContext",
    "finishReadingContext",
    "readContext",
    "checkIfContextChanged",
]
