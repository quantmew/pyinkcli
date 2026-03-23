from __future__ import annotations

from .window_polyfill import installDevtoolsWindowPolyfill


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


__all__ = ["connectToDevTools", "connectWithCustomMessagingProtocol"]
