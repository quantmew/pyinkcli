"""Core components for pyinkcli."""

from importlib import import_module
from typing import Any

_EXPORTS = {
    "App": ("pyinkcli.components.App", "App"),
    "ErrorBoundary": ("pyinkcli.components.ErrorBoundary", "ErrorBoundary"),
    "ErrorOverview": ("pyinkcli.components.ErrorOverview", "ErrorOverview"),
    "Box": ("pyinkcli.components.Box", "Box"),
    "Text": ("pyinkcli.components.Text", "Text"),
    "Newline": ("pyinkcli.components.Newline", "Newline"),
    "Spacer": ("pyinkcli.components.Spacer", "Spacer"),
    "Static": ("pyinkcli.components.Static", "Static"),
    "Transform": ("pyinkcli.components.Transform", "Transform"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
