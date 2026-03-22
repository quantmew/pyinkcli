from __future__ import annotations

from types import SimpleNamespace

from .window_polyfill import installDevtoolsWindowPolyfill


def installHook():
    scope = installDevtoolsWindowPolyfill()
    hook = SimpleNamespace(
        supportsFiber=True,
        inject=lambda renderer: 1,
        emit=lambda *args, **kwargs: None,
    )
    scope["__REACT_DEVTOOLS_GLOBAL_HOOK__"] = hook
    return hook


def initialize():
    return installHook()


def connectToDevTools(options: dict):
    websocket = options["websocket"]
    websocket._devtools_listeners.append(
        lambda message: [
            renderer["dispatchBridgeMessage"](message)
            for renderer in installDevtoolsWindowPolyfill().get("__INK_DEVTOOLS_RENDERERS__", {}).values()
        ]
    )
    return lambda: websocket._devtools_listeners.clear()


def connectWithCustomMessagingProtocol(options: dict):
    return connectToDevTools(options)


__all__ = [
    "initialize",
    "installHook",
    "connectToDevTools",
    "connectWithCustomMessagingProtocol",
]

