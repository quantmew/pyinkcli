"""Compatibility exports for hook-specific reconciler helpers."""

from __future__ import annotations

from .ReactHooks import *  # noqa: F401,F403


def startHostTransition(*_args, **_kwargs):
    return None


__all__ = [name for name in globals() if not name.startswith("_")]
