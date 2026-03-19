"""Compatibility facade for the internal suspense runtime."""

from pyinkcli._suspense_runtime import (
    SuspendSignal,
    invalidateResource,
    peekResource,
    preloadResource,
    readResource,
    resetAllResources,
    resetResource,
)

__all__ = [
    "SuspendSignal",
    "readResource",
    "preloadResource",
    "peekResource",
    "invalidateResource",
    "resetResource",
    "resetAllResources",
]
