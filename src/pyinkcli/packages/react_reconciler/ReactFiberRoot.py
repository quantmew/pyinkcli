"""Root/container state aligned with ReactFiberRoot responsibilities."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field

from pyinkcli.packages.ink.dom import DOMElement
from pyinkcli.packages.react_reconciler.ReactEventPriorities import (
    NoEventPriority,
    UpdatePriority,
)


@dataclass
class ReconcilerContainer:
    container: DOMElement
    tag: int = 0
    hydrate: bool = False
    pending_updates: list[tuple[object | None, Callable[[], None] | None]] = field(
        default_factory=list
    )
    update_scheduled: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)
    pending_lanes: int = NoEventPriority
    suspended_lanes: int = NoEventPriority
    pinged_lanes: int = NoEventPriority
    finished_lanes: int = NoEventPriority
    callback_priority: UpdatePriority = NoEventPriority
    update_requested: bool = False
    update_running: bool = False
    pending_update_priority: UpdatePriority = NoEventPriority
    current_update_priority: UpdatePriority = NoEventPriority


__all__ = ["ReconcilerContainer"]
