"""Shared internals surface bridging React client and reconciler state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class _SharedInternals:
    H: Any | None = None
    A: Any | None = None
    T: object | None = None
    S: Any | None = None
    G: Any | None = None
    actQueue: list[Any] | None = None
    asyncTransitions: int = 0
    isBatchingLegacy: bool = False
    didScheduleLegacyUpdate: bool = False
    didUsePromise: bool = False
    thrownErrors: list[Any] = field(default_factory=list)
    getCurrentStack: Any | None = None
    recentlyCreatedOwnerStacks: int = 0
    current_update_priority: int = 0
    current_render_priority: int = 0

    @property
    def current_transition(self) -> object | None:
        return self.T

    @current_transition.setter
    def current_transition(self, value: object | None) -> None:
        self.T = value


shared_internals = _SharedInternals()


__all__ = ["shared_internals"]
