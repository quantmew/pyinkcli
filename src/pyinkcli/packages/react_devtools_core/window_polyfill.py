from __future__ import annotations

import builtins
from typing import Any


DEFAULT_COMPONENT_FILTERS = [
    {"type": 2, "value": "InternalApp"},
    {"type": 2, "value": "InternalFocusContext"},
]


def _get_scope() -> dict[str, Any]:
    scope = builtins.__dict__.setdefault("__INK_DEVTOOLS_GLOBAL__", {})
    scope.setdefault("__INK_DEVTOOLS_RENDERERS__", {})
    scope.setdefault("__REACT_DEVTOOLS_COMPONENT_FILTERS__", list(DEFAULT_COMPONENT_FILTERS))
    scope.setdefault("__INK_DEVTOOLS_LAST_COPIED_VALUE__", None)
    scope.setdefault("__INK_DEVTOOLS_LAST_LOGGED_ELEMENT__", None)
    scope.setdefault("__INK_DEVTOOLS_STOP_INSPECTING_HOST__", False)
    return scope


class DevtoolsHook:
    def __init__(self, scope: dict[str, Any]) -> None:
        self.supportsFiber = True
        self._scope = scope
        self._listeners: dict[str, list] = {}
        self.rendererInterfaces: dict[int, Any] = {}
        self.renderers: dict[int, Any] = scope["__INK_DEVTOOLS_RENDERERS__"]

    def sub(self, event: str, listener):
        self._listeners.setdefault(event, []).append(listener)

        def unsubscribe() -> None:
            listeners = self._listeners.get(event, [])
            if listener in listeners:
                listeners.remove(listener)

        return unsubscribe

    def on(self, event: str, listener):
        return self.sub(event, listener)

    def emit(self, event: str, *args, **kwargs) -> None:
        for listener in list(self._listeners.get(event, [])):
            listener(*args, **kwargs)

    def inject(self, internals: dict[str, Any]):
        renderer_id = internals.get("rendererID")
        if not isinstance(renderer_id, int):
            renderer_id = id(internals)
            internals["rendererID"] = renderer_id
        self.renderers[renderer_id] = internals
        self.rendererInterfaces[renderer_id] = internals
        self._scope["__INK_RECONCILER_DEVTOOLS_METADATA__"] = internals
        return renderer_id


def installDevtoolsWindowPolyfill() -> dict[str, Any]:
    scope = _get_scope()
    hook = scope.get("__REACT_DEVTOOLS_GLOBAL_HOOK__")
    if not isinstance(hook, DevtoolsHook):
        hook = DevtoolsHook(scope)
        scope["__REACT_DEVTOOLS_GLOBAL_HOOK__"] = hook
    return scope

