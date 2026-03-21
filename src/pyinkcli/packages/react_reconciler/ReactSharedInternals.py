"""Minimal shared internals surface for reconciler scheduling state."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _SharedInternals:
    current_update_priority: int = 0
    current_render_priority: int = 0
    current_transition: object | None = None


shared_internals = _SharedInternals()


__all__ = ["shared_internals"]
