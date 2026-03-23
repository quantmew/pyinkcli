from __future__ import annotations

from types import SimpleNamespace

from .window_polyfill import installDevtoolsWindowPolyfill


def installHook():
    scope = installDevtoolsWindowPolyfill()
    hook = SimpleNamespace(
        supportsFiber=True,
        inject=lambda renderer: 1,
        emit=lambda *args, **kwargs: None,
    )
    scope["__REACT_DEVTOOLS_GLOBAL_HOOK__"] = hook
    return hook


def initialize():
    return installHook()


__all__ = ["initialize", "installHook"]
