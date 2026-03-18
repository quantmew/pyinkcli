"""Devtools integration matching JS `devtools.ts`."""

from __future__ import annotations

import socket
import warnings

from ink_python.devtools_window_polyfill import installDevtoolsWindowPolyfill


def isDevToolsReachable(host: str = "127.0.0.1", port: int = 8097, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def initializeDevtools() -> bool:
    installDevtoolsWindowPolyfill()
    if isDevToolsReachable():
        return True

    warnings.warn(
        "DEV is set to true, but the React DevTools server is not running.",
        stacklevel=2,
    )
    return False
