from __future__ import annotations

from ._runtime import _trace, useLayoutEffect, useRef
from .use_app import useApp
from .use_stdin import useStdinContext

def _dispatch_paste(value: str) -> None:
    useStdinContext().internal_eventEmitter.emit("paste", value)


def _clear_paste_handlers() -> None:
    useStdinContext().internal_eventEmitter.clear("paste")


def usePaste(handler=None, *, is_active: bool = True, isActive: bool | None = None):
    if handler is None:
        return None
    handler_ref = useRef(handler)
    handler_ref.current = handler
    app = useApp()
    stdin = useStdinContext()
    active = is_active if isActive is None else bool(isActive)

    def manage_terminal_modes():
        if not active:
            return None
        stdin.setRawMode(True)
        stdin.setBracketedPasteMode(True)

        def cleanup():
            stdin.setRawMode(False)
            stdin.setBracketedPasteMode(False)

        return cleanup

    useLayoutEffect(manage_terminal_modes, (active,))

    def effect():
        if not active:
            return None

        def handle_paste(value: str) -> None:
            _trace("hooks.paste.raw", bytes=len(value), value=value[:20])
            if app is not None:
                _trace("hooks.paste.discrete_begin")
                app._run_discrete(lambda: handler_ref.current(value))
            else:
                _trace("hooks.paste.invoke_sync")
                handler_ref.current(value)

        stdin.internal_eventEmitter.on("paste", handle_paste)

        def cleanup():
            stdin.internal_eventEmitter.off("paste", handle_paste)

        return cleanup

    useLayoutEffect(effect, (active,))
    return handler


__all__ = ["usePaste", "_dispatch_paste", "_clear_paste_handlers"]
