from __future__ import annotations

from ._runtime import useEffect, useRef
from .use_app import useApp

_paste_handlers: dict[str, object] = {}


def _dispatch_paste(value: str) -> None:
    app = useApp()
    if app is not None:
        app._run_discrete(lambda: [handler(value) for handler in list(_paste_handlers.values())])
        return
    for handler in list(_paste_handlers.values()):
        handler(value)


def _clear_paste_handlers() -> None:
    _paste_handlers.clear()


def usePaste(handler=None):
    if handler is None:
        return None
    handler_ref = useRef(handler)
    handler_ref.current = handler
    app = useApp()

    def effect():
        component_key = str(id(handler_ref))
        _paste_handlers[component_key] = lambda value: handler_ref.current(value)
        if app is not None:
            app._register_paste_interest()

        def cleanup():
            _paste_handlers.pop(component_key, None)
            if app is not None:
                app._unregister_paste_interest()

        return cleanup

    useEffect(effect, ())
    return handler


__all__ = ["usePaste", "_dispatch_paste", "_clear_paste_handlers"]
