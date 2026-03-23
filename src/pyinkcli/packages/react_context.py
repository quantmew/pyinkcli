from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from ..hooks import _runtime as hooks_runtime


@dataclass
class _Context:
    default_value: Any
    current_value: Any
    Provider: Any = None
    Consumer: Any = None


class _ProviderType:
    __ink_react_provider__ = True

    def __init__(self, context: _Context) -> None:
        self._context = context


class _ConsumerType:
    __ink_react_consumer__ = True

    def __init__(self, context: _Context) -> None:
        self._context = context


def createContext(default_value: Any) -> _Context:
    context = _Context(default_value=default_value, current_value=default_value)
    context.Provider = _ProviderType(context)
    context.Consumer = _ConsumerType(context)
    return context


def useContext(context: _Context) -> Any:
    return hooks_runtime.useContext(context)


class _SharedInternals(SimpleNamespace):
    H: Any = None


ReactSharedInternals = _SharedInternals()


__all__ = ["ReactSharedInternals", "createContext", "useContext"]
