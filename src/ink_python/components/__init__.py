"""Core components for ink-python."""

from importlib import import_module
from typing import Any

_EXPORTS = {
    "App": ("ink_python.components.App", "App"),
    "ErrorBoundary": ("ink_python.components.ErrorBoundary", "ErrorBoundary"),
    "ErrorOverview": ("ink_python.components.ErrorOverview", "ErrorOverview"),
    "Box": ("ink_python.components.Box", "Box"),
    "Text": ("ink_python.components.Text", "Text"),
    "Newline": ("ink_python.components.Newline", "Newline"),
    "Spacer": ("ink_python.components.Spacer", "Spacer"),
    "Static": ("ink_python.components.Static", "Static"),
    "Transform": ("ink_python.components.Transform", "Transform"),
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
