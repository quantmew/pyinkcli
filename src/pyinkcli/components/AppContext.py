from __future__ import annotations

from ..packages.react_context import createContext

Props = dict


class AppHandle:
    def __init__(self, app) -> None:
        object.__setattr__(self, "_app", app)

    def __getattr__(self, name):
        return getattr(self._app, name)

    def __setattr__(self, name, value):
        if name == "_app":
            object.__setattr__(self, name, value)
            return
        setattr(self._app, name, value)

    def waitUntilExit(self, timeout=None):
        return self._app.wait_until_exit(timeout=timeout)

    def waitUntilRenderFlush(self, timeout=None):
        return self._app.wait_until_render_flush(timeout=timeout)

    def exit(self, errorOrResult=None):
        return self._app.exit(errorOrResult)


def create_app_context_value(app=None):
    if app is None:
        return AppHandle(_NullApp())
    return AppHandle(app)


class _NullApp:
    def _run_discrete(self, callback):
        return None

    def _rerender_current(self):
        return None

    def wait_until_exit(self, timeout=None):
        return None

    def wait_until_render_flush(self, timeout=None):
        return None

    def exit(self, error_or_result=None):
        return None


AppContext = createContext(create_app_context_value())
AppContext.displayName = "InternalAppContext"


def set_app_context_value(app=None):
    value = create_app_context_value(app)
    AppContext.current_value = value
    return value

__all__ = ["AppContext", "Props"]
