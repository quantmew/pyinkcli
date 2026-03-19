"""React DevTools Core-aligned namespace for pyinkcli internals."""

from pyinkcli.packages.react_devtools_core.backend import (
    CURRENT_BRIDGE_PROTOCOL,
    createBackend,
    initializeBackend,
    isBackendReachable,
)
from pyinkcli.packages.react_devtools_core.hydration import (
    dispatch_bridge_message,
    handle_inspect_element_bridge_call,
    make_bridge_call,
    make_bridge_notification,
    make_bridge_success_response,
    normalize_inspect_element_bridge_payload,
    normalize_inspect_screen_bridge_payload,
)
from pyinkcli.packages.react_devtools_core.window_polyfill import (
    installDevtoolsWindowPolyfill,
)

__all__ = [
    "CURRENT_BRIDGE_PROTOCOL",
    "createBackend",
    "dispatch_bridge_message",
    "handle_inspect_element_bridge_call",
    "initializeBackend",
    "installDevtoolsWindowPolyfill",
    "isBackendReachable",
    "make_bridge_call",
    "make_bridge_notification",
    "make_bridge_success_response",
    "normalize_inspect_element_bridge_payload",
    "normalize_inspect_screen_bridge_payload",
]
