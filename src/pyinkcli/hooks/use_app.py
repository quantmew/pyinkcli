from __future__ import annotations

from ..components.AppContext import AppHandle

_current_app = None


def _set_current_app(app) -> None:
    global _current_app
    _current_app = app


def useApp():
    if _current_app is None:
        return None
    return AppHandle(_current_app)


__all__ = ["AppHandle", "useApp", "_set_current_app"]
