from __future__ import annotations

from importlib import import_module

__all__ = [
    "react",
    "react_devtools_core",
    "react_reconciler",
    "react_router",
]


def __getattr__(name: str):
    if name in __all__:
        return import_module(f"{__name__}.{name}")
    raise AttributeError(name)
