from __future__ import annotations

from ._runtime import useEffect, useRef
from .use_stdin import useStdin
from ..parse_keypress import Key, parseKeypress

_input_handlers: dict[str, object] = {}


def _dispatch_input(value: str) -> None:
    key = parseKeypress(value)
    for handler in list(_input_handlers.values()):
        handler(value, key)


def _clear_input_handlers() -> None:
    _input_handlers.clear()
    useStdin().clear("input")


def useInput(handler) -> None:
    handler_ref = useRef(handler)
    handler_ref.current = handler
    stdin = useStdin()

    def effect():
        component_key = str(id(handler_ref))
        _input_handlers[component_key] = lambda input_char, key: handler_ref.current(input_char, key)
        stdin.on("input", _input_handlers[component_key])

        def cleanup():
            _input_handlers.pop(component_key, None)
            stdin.clear("input")
            for existing in list(_input_handlers.values()):
                stdin.on("input", existing)

        return cleanup

    useEffect(effect, ())


__all__ = ["Key", "useInput", "_clear_input_handlers", "_dispatch_input"]

