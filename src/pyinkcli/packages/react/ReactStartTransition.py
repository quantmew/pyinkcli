"""Transition helpers aligned with ReactStartTransition."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pyinkcli.packages.react_reconciler.ReactSharedInternals import shared_internals


def startTransition(scope: Callable[[], Any], options: dict[str, Any] | None = None) -> None:
    del options
    previous_transition = shared_internals.T
    current_transition: dict[str, Any] = {}
    if __debug__:
        current_transition["_updatedFibers"] = set()
    shared_internals.T = current_transition
    try:
        return_value = scope()
        on_finish = shared_internals.S
        if callable(on_finish):
            on_finish(current_transition, return_value)
    finally:
        shared_internals.T = previous_transition


__all__ = ["startTransition"]
