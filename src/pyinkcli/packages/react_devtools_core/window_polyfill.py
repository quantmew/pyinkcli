"""Devtools window polyfill matching JS `devtools-window-polyfill.ts`."""

from __future__ import annotations

import builtins
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _DevToolsGlobalHook:
    supportsFiber: bool = True
    isDisabled: bool = False
    renderers: dict[int, Any] = field(default_factory=dict)
    _listeners: dict[str, list[Callable[..., Any]]] = field(default_factory=dict)
    _next_renderer_id: int = 0

    def inject(self, internals: Any) -> int:
        self._next_renderer_id += 1
        renderer_id = self._next_renderer_id
        self.renderers[renderer_id] = internals
        return renderer_id

    def emit(self, event: str, *args: Any) -> None:
        for listener in list(self._listeners.get(event, ())):
            listener(*args)

    def on(self, event: str, listener: Callable[..., Any]) -> Callable[[], None]:
        listeners = self._listeners.setdefault(event, [])
        listeners.append(listener)

        def unsubscribe() -> None:
            current = self._listeners.get(event, [])
            if listener in current:
                current.remove(listener)

        return unsubscribe


def installDevtoolsWindowPolyfill() -> dict[str, object]:
    global_scope = builtins.__dict__.setdefault("__INK_DEVTOOLS_GLOBAL__", {})
    global_scope.setdefault("window", global_scope)
    global_scope.setdefault("self", global_scope)
    global_scope.setdefault("__INK_DEVTOOLS_RENDERERS__", {})
    global_scope.setdefault("__REACT_DEVTOOLS_GLOBAL_HOOK__", _DevToolsGlobalHook())
    global_scope.setdefault(
        "__REACT_DEVTOOLS_COMPONENT_FILTERS__",
        [
            {"type": 1, "value": 7, "isEnabled": True},
            {"type": 2, "value": "InternalApp", "isEnabled": True, "isValid": True},
            {"type": 2, "value": "InternalAppContext", "isEnabled": True, "isValid": True},
            {"type": 2, "value": "InternalStdoutContext", "isEnabled": True, "isValid": True},
            {"type": 2, "value": "InternalStderrContext", "isEnabled": True, "isValid": True},
            {"type": 2, "value": "InternalStdinContext", "isEnabled": True, "isValid": True},
            {"type": 2, "value": "InternalFocusContext", "isEnabled": True, "isValid": True},
        ],
    )
    return global_scope


installDevtoolsWindowPolyfill()
