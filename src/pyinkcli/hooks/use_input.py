from __future__ import annotations

from ..parse_keypress import Key, parseKeypress
from ._runtime import _trace, useLayoutEffect, useRef
from .use_app import useApp
from .use_stdin import useStdinContext

def _dispatch_input(value: str) -> None:
    useStdinContext().internal_eventEmitter.emit("input", value)


def _clear_input_handlers() -> None:
    useStdinContext().internal_eventEmitter.clear("input")


def useInput(handler, *, is_active: bool = True, isActive: bool | None = None) -> None:
    handler_ref = useRef(handler)
    handler_ref.current = handler
    app = useApp()
    stdin = useStdinContext()
    active = is_active if isActive is None else bool(isActive)

    def manage_raw_mode():
        if not active:
            return None
        stdin.setRawMode(True)

        def cleanup():
            stdin.setRawMode(False)

        return cleanup

    useLayoutEffect(manage_raw_mode, (active,))

    def effect():
        if not active:
            return None

        def handle_data(value: str) -> None:
            keypress = parseKeypress(value)
            key = keypress
            input_value = keypress.name if keypress.ctrl else keypress.sequence
            if input_value == "c" and key.ctrl and stdin.internal_exitOnCtrlC:
                return
            _trace(
                "hooks.input.raw",
                key=key.name,
                input=input_value,
                raw=value,
            )
            runtime_app = getattr(app, "_app", app)
            if runtime_app is not None and type(runtime_app).__name__ != "_NullApp":
                _trace("hooks.input.discrete_begin")
                app._run_discrete(lambda: handler_ref.current(input_value, key))
            else:
                _trace("hooks.input.invoke_sync")
                handler_ref.current(input_value, key)

        stdin.internal_eventEmitter.on("input", handle_data)

        def cleanup():
            stdin.internal_eventEmitter.off("input", handle_data)

        return cleanup

    useLayoutEffect(effect, (active,))


__all__ = ["Key", "useInput", "_clear_input_handlers", "_dispatch_input"]

