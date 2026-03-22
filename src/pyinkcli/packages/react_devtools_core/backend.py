from __future__ import annotations

import builtins
from typing import Any

from .window_polyfill import DevtoolsHook, installDevtoolsWindowPolyfill


def _scope() -> dict[str, Any]:
    return installDevtoolsWindowPolyfill()


def installHook(target: Any | None = None, *args, **kwargs) -> DevtoolsHook:
    scope = _scope() if target is None else target
    if "__REACT_DEVTOOLS_GLOBAL_HOOK__" in scope and isinstance(
        scope["__REACT_DEVTOOLS_GLOBAL_HOOK__"], DevtoolsHook
    ):
        return scope["__REACT_DEVTOOLS_GLOBAL_HOOK__"]
    hook = DevtoolsHook(scope)
    scope["__REACT_DEVTOOLS_GLOBAL_HOOK__"] = hook
    return hook


def initialize(
    maybeSettingsOrSettingsPromise: Any | None = None,
    shouldStartProfilingNow: bool = False,
    profilingSettings: Any | None = None,
    maybeComponentFiltersOrComponentFiltersPromise: Any | None = None,
):
    scope = _scope()
    return installHook(scope)


def initializeBackend(*args, **kwargs):
    initialize(*args, **kwargs)
    return True


def connectToDevTools(options: dict[str, Any] | None = None):
    scope = _scope()
    websocket = (options or {}).get("websocket")
    if websocket is None:
        return lambda: None

    listeners = getattr(websocket, "_devtools_listeners", None)
    if listeners is None:
        listeners = []
        websocket._devtools_listeners = listeners

    def listener(message: Any) -> None:
        renderers = scope.get("__INK_DEVTOOLS_RENDERERS__", {})
        for renderer in list(renderers.values()):
            dispatch = None
            if isinstance(renderer, dict):
                dispatch = renderer.get("dispatchBridgeMessage")
            else:
                dispatch = getattr(renderer, "dispatchBridgeMessage", None)
            if callable(dispatch):
                dispatch(message)

    listeners.append(listener)

    def unsubscribe() -> None:
        if listener in listeners:
            listeners.remove(listener)

    return unsubscribe


def connectWithCustomMessagingProtocol(options: dict[str, Any] | None = None):
    return connectToDevTools(options)

