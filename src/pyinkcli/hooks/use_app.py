from __future__ import annotations

from ..components.AppContext import AppContext, AppHandle, set_app_context_value
from ..packages.react_context import useContext

_current_app = None


def _set_current_app(app) -> None:
    global _current_app
    _current_app = app
    set_app_context_value(app)


def useApp():
    value = useContext(AppContext)
    if value is not None:
        return value
    if _current_app is None:
        return None
    return AppHandle(_current_app)


__all__ = ["AppHandle", "useApp", "_set_current_app"]
