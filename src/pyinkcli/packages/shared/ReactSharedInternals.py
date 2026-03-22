"""Mutable shared internals object used by React compatibility layers."""

from __future__ import annotations


class _SharedInternals:
    def __init__(self) -> None:
        self.H = None
        self.A = None
        self.T = None
        self.S = None
        self.G = None
        self.actQueue = None
        self.asyncTransitions = 0
        self.isBatchingLegacy = False
        self.didScheduleLegacyUpdate = False
        self.didUsePromise = False
        self.thrownErrors: list[BaseException | object] = []
        self.getCurrentStack = None
        self.recentlyCreatedOwnerStacks = 0
        self.current_render_priority = None
        self.current_update_priority = 0
        self.current_transition = None


shared_internals = _SharedInternals()
ReactSharedInternals = shared_internals


__all__ = ["ReactSharedInternals", "shared_internals"]
