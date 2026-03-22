from __future__ import annotations

_current_app = None


def _set_current_app(app) -> None:
    global _current_app
    _current_app = app


def useApp():
    return _current_app


__all__ = ["useApp", "_set_current_app"]

