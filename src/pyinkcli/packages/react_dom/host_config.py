"""Renderer host configuration shared between the terminal renderer and reconciler."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Literal, Optional

if TYPE_CHECKING:
    from pyinkcli.component import RenderableNode

UpdatePriority = Literal["default", "discrete", "render_phase"]


@dataclass
class ReconcilerHostConfig:
    get_current_component: Callable[[], Optional["RenderableNode | Callable"]]
    perform_render: Callable[[Any], None]
    wait_for_render_flush: Callable[[Optional[float]], None]
    request_render: Callable[[UpdatePriority, bool], None]


__all__ = ["ReconcilerHostConfig"]
