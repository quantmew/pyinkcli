from __future__ import annotations

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
        return {
            "exit": lambda error_or_result=None: None,
            "waitUntilRenderFlush": lambda timeout=None: None,
        }
    return AppHandle(app)


AppContext = create_app_context_value()

__all__ = ["AppContext", "Props"]
