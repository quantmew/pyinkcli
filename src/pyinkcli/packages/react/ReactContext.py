"""Context helpers aligned with ReactContext."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Generator, Generic, TypeVar

from pyinkcli._component_runtime import RenderableNode

T = TypeVar("T")


@dataclass
class _ReactConsumer(Generic[T]):
    _context: "ReactContext[T]"
    __ink_react_consumer__: bool = True


@dataclass
class _ReactProvider(Generic[T]):
    _context: "ReactContext[T]"
    __ink_react_provider__: bool = True


class ReactContext(Generic[T]):
    def __init__(self, default_value: T):
        self._currentValue = default_value
        self._currentValue2 = default_value
        self._threadCount = 0
        self._value = ContextVar("react_context_value", default=default_value)
        self.__ink_react_context__ = True
        self.Provider = _ReactProvider(self)
        self.Consumer = _ReactConsumer(self)

    @contextmanager
    def _provide(self, value: T) -> Generator[None, None, None]:
        token = self._value.set(value)
        previous = self._currentValue
        self._currentValue = value
        self._currentValue2 = value
        try:
            yield
        finally:
            self._currentValue = previous
            self._currentValue2 = previous
            self._value.reset(token)

    def get(self) -> T:
        return self._value.get()


def createContext(defaultValue: T) -> ReactContext[T]:
    return ReactContext(defaultValue)


__all__ = ["ReactContext", "createContext"]
