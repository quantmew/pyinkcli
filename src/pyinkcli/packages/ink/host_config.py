"""Shared host config types for the Ink renderer and reconciler."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyinkcli.component import RenderableNode

UpdatePriority = int


@dataclass
class ReconcilerHostConfig:
    get_current_component: Callable[[], RenderableNode | Callable | None]
    perform_render: Callable[[Any], None]
    wait_for_render_flush: Callable[[float | None], None]
    request_render: Callable[[UpdatePriority, bool], None]


__all__ = ["ReconcilerHostConfig", "UpdatePriority"]
