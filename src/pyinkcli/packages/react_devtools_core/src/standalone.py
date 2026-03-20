"""Source standalone implementation mirroring react-devtools-core/src/standalone.js."""

from __future__ import annotations

import socketserver
import threading
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any, Literal

from pyinkcli.packages.react_devtools_core.src.editor import (
    doesFilePathExist,
    launchEditor,
)
from pyinkcli.packages.react_devtools_core.window_polyfill import (
    installDevtoolsWindowPolyfill,
)

StatusType = Literal["server-connected", "devtools-connected", "error"]
StatusListener = Callable[[str, StatusType], None]
DisconnectedCallback = Callable[[], None]


def _default_status_listener(_message: str, _status: StatusType) -> None:
    return None


def _default_disconnected_callback() -> None:
    return None


@dataclass
class _StandaloneState:
    content_dom_node: Any = None
    project_roots: list[str] = field(default_factory=list)
    status_listener: StatusListener = _default_status_listener
    disconnected_callback: DisconnectedCallback = _default_disconnected_callback
    bridge_socket: Any = None
    profiler_opened: bool = False
    last_server: dict[str, Any] | None = None


@dataclass
class _CloseHandle:
    close: Callable[[], None]


class _SilentTCPHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        try:
            self.request.recv(4096)
        except OSError:
            return


class _ThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


class _DevToolsUI:
    def __init__(self) -> None:
        self._state = _StandaloneState()

    def setContentDOMNode(self, value: Any) -> _DevToolsUI:
        self._state.content_dom_node = value
        return self

    def setProjectRoots(self, value: list[str]) -> _DevToolsUI:
        self._state.project_roots = list(value)
        return self

    def setStatusListener(self, value: StatusListener) -> _DevToolsUI:
        self._state.status_listener = value
        return self

    def setDisconnectedCallback(self, value: DisconnectedCallback) -> _DevToolsUI:
        self._state.disconnected_callback = value
        return self

    def openProfiler(self) -> None:
        installDevtoolsWindowPolyfill()["__REACT_DEVTOOLS_DEFAULT_TAB__"] = "profiler"
        self._state.profiler_opened = True

    def canViewElementSource(self, _source: Any, symbolicated_source: Any) -> bool:
        if not symbolicated_source or len(symbolicated_source) < 2:
            return False

        source_url = symbolicated_source[1]
        return doesFilePathExist(source_url, self._state.project_roots)

    def viewElementSource(self, _source: Any, symbolicated_source: Any) -> bool:
        if not symbolicated_source or len(symbolicated_source) < 3:
            return False

        source_url = symbolicated_source[1]
        line = symbolicated_source[2]
        return launchEditor(source_url, line, self._state.project_roots)

    def connectToSocket(self, socket: Any) -> _CloseHandle:
        installDevtoolsWindowPolyfill()
        self._state.bridge_socket = socket

        with suppress(Exception):
            socket.onerror = lambda _error=None: self._on_disconnected()
        with suppress(Exception):
            socket.onclose = lambda: self._on_disconnected()

        self._state.status_listener("DevTools initialized.", "devtools-connected")
        return _CloseHandle(close=self._on_disconnected)

    def startServer(
        self,
        port: int = 8097,
        host: str = "localhost",
        httpsOptions: dict[str, Any] | None = None,
        loggerOptions: dict[str, Any] | None = None,
        path: str | None = None,
        clientOptions: dict[str, Any] | None = None,
    ) -> _CloseHandle:
        del httpsOptions, loggerOptions, path, clientOptions

        installDevtoolsWindowPolyfill()

        try:
            server = _ThreadingTCPServer((host, port), _SilentTCPHandler)
        except OSError:
            self._state.status_listener("Failed to start the server.", "error")
            raise

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        actual_host, actual_port = server.server_address[:2]
        self._state.last_server = {
            "host": actual_host,
            "port": actual_port,
        }
        self._state.status_listener(
            f"The server is listening on the port {actual_port}.",
            "server-connected",
        )

        def close() -> None:
            self._on_disconnected()
            server.shutdown()
            server.server_close()
            thread.join(timeout=0.5)

        return _CloseHandle(close=close)

    def _on_disconnected(self) -> None:
        self._state.bridge_socket = None
        self._state.disconnected_callback()


DevtoolsUI = _DevToolsUI()

__all__ = [
    "DevtoolsUI",
    "DisconnectedCallback",
    "StatusListener",
    "StatusType",
]
