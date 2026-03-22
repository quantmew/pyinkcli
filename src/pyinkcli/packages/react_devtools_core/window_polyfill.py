from __future__ import annotations

import builtins


def installDevtoolsWindowPolyfill():
    scope = builtins.__dict__.setdefault("__INK_DEVTOOLS_GLOBAL__", {})
    scope.setdefault("__INK_DEVTOOLS_RENDERERS__", {})
    scope.setdefault(
        "__REACT_DEVTOOLS_COMPONENT_FILTERS__",
        [
            {"type": 2, "value": "InternalApp"},
            {"type": 2, "value": "InternalFocusContext"},
        ],
    )
    return scope


__all__ = ["installDevtoolsWindowPolyfill"]

