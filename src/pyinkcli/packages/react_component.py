from __future__ import annotations

from typing import Any


class _NoopUpdater:
    def enqueueSetState(self, public_instance, partial_state, callback=None, callerName=None):
        if callable(partial_state):
            partial_state = partial_state(public_instance.state, public_instance.props)
        if isinstance(partial_state, dict):
            public_instance.state.update(partial_state)
        if callback:
            callback()

    def enqueueForceUpdate(self, public_instance, callback=None, callerName=None):
        if callback:
            callback()


class Component:
    def __init__(self, props: dict[str, Any] | None = None, context: Any = None, updater: Any = None) -> None:
        self.props = props or {}
        self.context = context
        self.refs = {}
        self.state = {}
        self.updater = updater or _NoopUpdater()

    def setState(self, partial_state, callback=None) -> None:
        if partial_state is not None and not callable(partial_state) and not isinstance(partial_state, dict):
            raise TypeError("setState(...) takes an object of state variables to update")
        self.updater.enqueueSetState(self, partial_state, callback, "setState")

    def forceUpdate(self, callback=None) -> None:
        self.updater.enqueueForceUpdate(self, callback, "forceUpdate")


__all__ = ["Component"]
