from __future__ import annotations

from .packages.react import Component


class _Component(Component):
    isReactComponent = True

    def set_state(self, partial_state, callback=None) -> None:
        self.setState(partial_state, callback)

    def force_update(self, callback=None) -> None:
        self.forceUpdate(callback)


__all__ = ["_Component"]
