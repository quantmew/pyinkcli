"""Shared internal state used by the hook/runtime layer."""

from __future__ import annotations

from dataclasses import dataclass

from .ReactEventPriorities import NoEventPriority


@dataclass
class _SharedInternals:
    H: object | None = None
    A: object | None = None
    current_transition: object | None = None
    current_update_priority: int = NoEventPriority
    current_render_priority: int = NoEventPriority
    isBatchingLegacy: bool = False
    actQueue: object | None = None
    didScheduleLegacyUpdate: bool = False
    getCurrentStack: object | None = None


shared_internals = _SharedInternals()
