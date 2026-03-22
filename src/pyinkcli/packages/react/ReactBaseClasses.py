"""Base component classes aligned with ReactBaseClasses.js."""

from __future__ import annotations

from typing import Any, Callable

from pyinkcli._component_runtime import _Component


class Ref:
    def __init__(self, current: Any = None) -> None:
        self.current = current


def createRef() -> Ref:
    return Ref()


class Component(_Component):
    isReactComponent = {}

    def __init__(
        self,
        props: dict[str, Any] | None = None,
        context: object | None = None,
        refs: object | None = None,
        updater: object | None = None,
        **extra_props: Any,
    ) -> None:
        merged_props = dict(props or {})
        merged_props.update(extra_props)
        super().__init__(**merged_props)
        self.context = context
        self.refs = refs or {}
        self.updater = updater

    def setState(
        self,
        partialState,
        callback: Callable[[], None] | None = None,
    ) -> None:
        if (
            partialState is not None
            and not callable(partialState)
            and not isinstance(partialState, dict)
        ):
            raise TypeError(
                "setState(...): takes an object of state variables to update or a function which returns an object of state variables."
            )
        if hasattr(self.updater, "enqueueSetState"):
            self.updater.enqueueSetState(self, partialState, callback, "setState")
        else:
            self.set_state(partialState)
            if callable(callback):
                callback()

    def forceUpdate(self, callback: Callable[[], None] | None = None) -> None:
        if hasattr(self.updater, "enqueueForceUpdate"):
            self.updater.enqueueForceUpdate(self, callback, "forceUpdate")
        else:
            self.force_update()
            if callable(callback):
                callback()


class PureComponent(Component):
    isPureReactComponent = True


__all__ = ["Component", "PureComponent", "Ref", "createRef"]
