"""Base class helpers aligned with ReactBaseClasses."""

from __future__ import annotations

from typing import Any

from pyinkcli._component_runtime import _Component
from pyinkcli.packages.react.ReactNoopUpdateQueue import ReactNoopUpdateQueue


class Component(_Component):
    isReactComponent: dict[str, bool] = {}

    def __init__(
        self,
        props: dict[str, Any] | None = None,
        context: Any = None,
        updater: Any = None,
        **kwargs: Any,
    ):
        merged_props = dict(props or {})
        merged_props.update(kwargs)
        super().__init__(**merged_props)
        self.context = context
        self.refs: dict[str, Any] = {}
        self.updater = updater or ReactNoopUpdateQueue

    def setState(self, partialState: Any, callback: Any = None) -> None:
        if (
            not isinstance(partialState, dict)
            and not callable(partialState)
            and partialState is not None
        ):
            raise TypeError(
                "takes an object of state variables to update or a function which returns an object of state variables."
            )
        self.updater.enqueueSetState(self, partialState, callback, "setState")

    def forceUpdate(self, callback: Any = None) -> None:
        self.updater.enqueueForceUpdate(self, callback, "forceUpdate")


class PureComponent(Component):
    isPureReactComponent = True


__all__ = ["Component", "PureComponent"]
