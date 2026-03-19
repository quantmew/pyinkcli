"""Thin entrypoint for React DevTools backend integration."""

from __future__ import annotations

import warnings
import socket

from pyinkcli.packages.react_devtools_core.backend_constants import (
    CURRENT_BRIDGE_PROTOCOL,
)
from pyinkcli.packages.react_devtools_core.backend_facade import (
    createBackend,
)
from pyinkcli.packages.react_devtools_core.window_polyfill import (
    installDevtoolsWindowPolyfill,
)


_devtools_initialized: bool = False


def isBackendReachable(host: str = "localhost", port: int = 8097, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def initializeBackend() -> bool:
    global _devtools_initialized
    if _devtools_initialized:
        return True

    installDevtoolsWindowPolyfill()
    if isBackendReachable():
        _devtools_initialized = True
        return True

    warnings.warn(
        "DEV is set to true, but the React DevTools server is not running. "
        "Start it with:\n\n$ npx react-devtools\n",
        stacklevel=2,
    )
    return False


__all__ = [
    "CURRENT_BRIDGE_PROTOCOL",
    "createBackend",
    "initializeBackend",
    "installDevtoolsWindowPolyfill",
    "isBackendReachable",
]
