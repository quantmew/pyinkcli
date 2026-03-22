"""Host-config contract used by the reconciler/Ink integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class ReconcilerHostConfig:
    get_current_component: Callable[[], Any] | None = None
    perform_render: Callable[[Any, int], bool] | None = None
    wait_for_render_flush: Callable[[float | None], None] | None = None
    request_render: Callable[[int, bool], None] | None = None
    schedule_resume: Callable[[int], None] | None = None
    should_defer_sync_passive_effects_to_commit: Callable[[], bool] | None = None

