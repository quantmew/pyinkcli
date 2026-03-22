from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from .src.editor import doesFilePathExist, launchEditor


class _DevtoolsUI:
    def __init__(self) -> None:
        self._node = None
        self._waiting_html = ""
        self._project_roots: list[str] = []
        self._status_listener = lambda message, status=None: None
        self._disconnected_callback = lambda: None

    def setContentDOMNode(self, value):
        self._node = value
        self._waiting_html = getattr(value, "innerHTML", "")
        return self

    def setProjectRoots(self, value):
        self._project_roots = list(value)
        return self

    def setStatusListener(self, value):
        self._status_listener = value
        return self

    def setDisconnectedCallback(self, value):
        self._disconnected_callback = value
        return self

    def canViewElementSource(self, _source, symbolicatedSource):
        if symbolicatedSource is None:
            return False
        _, sourceURL, _line = symbolicatedSource
        return doesFilePathExist(sourceURL, self._project_roots)

    def viewElementSource(self, _source, symbolicatedSource):
        if symbolicatedSource is None:
            return None
        _, sourceURL, line = symbolicatedSource
        return launchEditor(sourceURL, line, self._project_roots)

    def connectToSocket(self, socket):
        def onclose(*_args, **_kwargs):
            self._disconnected_callback()

        def onerror(*_args, **_kwargs):
            self._disconnected_callback()

        socket.onclose = onclose
        socket.onerror = onerror

        listeners = getattr(socket, "_devtools_listeners", None)
        if listeners is None:
            listeners = []
            socket._devtools_listeners = listeners

        def listener(message: Any) -> None:
            pass

        listeners.append(listener)

        def close():
            self._disconnected_callback()
            if listener in listeners:
                listeners.remove(listener)

        return SimpleNamespace(close=close)

    def startServer(self, *args, **kwargs):
        self._status_listener("The server is listening.", "server-connected")

        def close():
            self._disconnected_callback()

        return SimpleNamespace(close=close)

    def openProfiler(self):
        self._status_listener("DevTools initialized.", "devtools-connected")
        return None


DevtoolsUI = _DevtoolsUI()

