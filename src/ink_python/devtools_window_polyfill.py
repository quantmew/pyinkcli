"""Devtools window polyfill matching JS `devtools-window-polyfill.ts`."""

from __future__ import annotations

import builtins


def installDevtoolsWindowPolyfill() -> dict[str, object]:
    global_scope = builtins.__dict__.setdefault("__INK_DEVTOOLS_GLOBAL__", {})
    global_scope.setdefault("window", global_scope)
    global_scope.setdefault("self", global_scope)
    global_scope.setdefault("__INK_DEVTOOLS_RENDERERS__", {})
    global_scope.setdefault(
        "__REACT_DEVTOOLS_COMPONENT_FILTERS__",
        [
            {"type": 1, "value": 7, "isEnabled": True},
            {"type": 2, "value": "InternalApp", "isEnabled": True, "isValid": True},
            {"type": 2, "value": "InternalAppContext", "isEnabled": True, "isValid": True},
            {"type": 2, "value": "InternalStdoutContext", "isEnabled": True, "isValid": True},
            {"type": 2, "value": "InternalStderrContext", "isEnabled": True, "isValid": True},
            {"type": 2, "value": "InternalStdinContext", "isEnabled": True, "isValid": True},
            {"type": 2, "value": "InternalFocusContext", "isEnabled": True, "isValid": True},
        ],
    )
    return global_scope


installDevtoolsWindowPolyfill()
