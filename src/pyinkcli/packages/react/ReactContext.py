"""React context helpers."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from pyinkcli._component_runtime import scopeRender
from pyinkcli.packages.react.ReactBaseClasses import Component
from pyinkcli.packages.shared.ReactSymbols import REACT_CONSUMER_TYPE, REACT_CONTEXT_TYPE


class ReactContext:
    def __init__(self, default_value: Any) -> None:
        self.__dict__["$$typeof"] = REACT_CONTEXT_TYPE
        self._currentValue = default_value
        self._currentValue2 = default_value
        self._default_value = default_value
        self._threadCount = 0
        self._currentRenderer = None
        self._currentRenderer2 = None
        self.displayName = None
        self.Provider = None
        self.Consumer = None


def createContext(defaultValue: Any) -> ReactContext:
    context = ReactContext(defaultValue)

    class Provider(Component):
        __ink_react_provider__ = True

        def render(self):
            children = self.props.get("children")
            value = self.props.get("value", context._currentValue)

            @contextmanager
            def provider_scope():
                previous_value = context._currentValue
                previous_value2 = context._currentValue2
                context._currentValue = value
                context._currentValue2 = value
                try:
                    yield
                finally:
                    context._currentValue = previous_value
                    context._currentValue2 = previous_value2

            return scopeRender(children, provider_scope)

    setattr(Provider, "$$typeof", REACT_CONTEXT_TYPE)
    Provider._context = context

    def Consumer(*children, **props):
        child = children[0] if children else props.get("children")
        if isinstance(child, (list, tuple)) and child:
            child = child[0]
        if callable(child):
            return child(context._currentValue)
        return child

    setattr(Consumer, "$$typeof", REACT_CONSUMER_TYPE)
    Consumer.__ink_react_consumer__ = True
    Consumer._context = context

    context.Provider = Provider
    context.Consumer = Consumer
    return context


__all__ = ["createContext", "ReactContext"]
