"""Host config surface aligned with ReactFiberConfig responsibilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Optional

from pyinkcli.packages.react_reconciler.ReactEventPriorities import UpdatePriority

if TYPE_CHECKING:
    from pyinkcli.component import RenderableNode


@dataclass
class ReconcilerHostConfig:
    get_current_component: Callable[[], Optional["RenderableNode | Callable"]]
    perform_render: Callable[[Any], None]
    wait_for_render_flush: Callable[[Optional[float]], None]
    request_render: Callable[[UpdatePriority, bool], None]


__all__ = ["ReconcilerHostConfig"]

