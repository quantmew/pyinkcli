from __future__ import annotations

_window_size = (80, 24)


def _set_window_size(columns: int, rows: int) -> None:
    global _window_size
    _window_size = (columns, rows)


def useWindowSize():
    return _window_size


__all__ = ["useWindowSize", "_set_window_size"]

