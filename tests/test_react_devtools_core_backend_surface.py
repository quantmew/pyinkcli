from __future__ import annotations

import builtins

from pyinkcli.packages.react_devtools_core import (
    connectToDevTools,
    initialize,
)
from pyinkcli.packages.react_devtools_core.window_polyfill import (
    installDevtoolsWindowPolyfill,
)


class FakeWebSocket:
    OPEN = 1

    def __init__(self) -> None:
        self.readyState = self.OPEN
        self.sent_messages: list[object] = []
        self._devtools_listeners: list[object] = []
        self.onopen = None

    def send(self, message: object) -> None:
        self.sent_messages.append(message)


def test_initialize_installs_devtools_hook() -> None:
    global_scope = installDevtoolsWindowPolyfill()
    global_scope.pop("__REACT_DEVTOOLS_GLOBAL_HOOK__", None)

    initialize()

    restored_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
    hook = restored_scope["__REACT_DEVTOOLS_GLOBAL_HOOK__"]
    assert getattr(hook, "supportsFiber") is True
    assert callable(getattr(hook, "inject"))
    assert callable(getattr(hook, "emit"))


def test_connect_to_devtools_registers_custom_messaging_listener() -> None:
    global_scope = installDevtoolsWindowPolyfill()
    initialize()
    global_scope["__INK_DEVTOOLS_RENDERERS__"] = {
        1: {
            "dispatchBridgeMessage": lambda message: message,
        }
    }
    websocket = FakeWebSocket()

    unsubscribe = connectToDevTools({"websocket": websocket})

    assert callable(unsubscribe)
    assert len(websocket._devtools_listeners) == 1
