from __future__ import annotations

from collections import defaultdict


class _StdinHandle:
    def __init__(self) -> None:
        self._listeners = defaultdict(list)

    def on(self, event: str, listener) -> None:
        if listener not in self._listeners[event]:
            self._listeners[event].append(listener)

    def emit(self, event: str, *args) -> None:
        for listener in list(self._listeners[event]):
            listener(*args)

    def listener_count(self, event: str) -> int:
        return len(self._listeners[event])

    def clear(self, event: str | None = None) -> None:
        if event is None:
            self._listeners.clear()
        else:
            self._listeners[event].clear()


_stdin = _StdinHandle()


def useStdin() -> _StdinHandle:
    return _stdin


def useStdinContext() -> _StdinHandle:
    return _stdin


__all__ = ["useStdin", "useStdinContext", "_StdinHandle"]

