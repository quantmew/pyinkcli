from __future__ import annotations

from .packages.react import Component


class _Component(Component):
    isReactComponent = True


__all__ = ["_Component"]

