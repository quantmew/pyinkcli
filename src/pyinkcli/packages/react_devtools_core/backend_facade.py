"""Composition layer for the React DevTools backend facade."""

from __future__ import annotations

from typing import Any

from pyinkcli.packages.react_devtools_core.backend_agent_facade import (
    createAgent,
)
from pyinkcli.packages.react_devtools_core.backend_bridge_facade import (
    createBridgeDispatcher,
)


def createBackend(
    renderer_interface: dict[str, Any],
) -> dict[str, Any]:
    backend_state = {
        "lastNotification": None,
        "lastStopInspectingHostSelected": None,
        "lastSelectedElementID": None,
        "lastSelectedRendererID": None,
        "persistedSelection": None,
        "persistedSelectionMatch": None,
    }

    bridge_dispatcher = createBridgeDispatcher(
        renderer_interface,
        state=backend_state,
    )
    agent_methods = createAgent(
        renderer_interface,
        state=backend_state,
        dispatch_message=bridge_dispatcher["dispatchBridgeMessage"],
    )

    return {
        "backendState": backend_state,
        **bridge_dispatcher,
        **agent_methods,
    }


__all__ = ["createBackend"]
