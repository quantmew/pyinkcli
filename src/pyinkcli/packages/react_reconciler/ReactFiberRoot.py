"""Root/container state aligned with ReactFiberRoot responsibilities."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

from pyinkcli.packages.ink.dom import DOMElement
from pyinkcli.packages.react_reconciler.ReactEventPriorities import UpdatePriority


@dataclass
class ReconcilerContainer:
    container: DOMElement
    tag: int = 0
    hydrate: bool = False
    pending_element: Optional[object] = None
    pending_callback: Optional[Callable[[], None]] = None
    work_scheduled: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)
    rerender_requested: bool = False
    rerender_running: bool = False
    pending_rerender_priority: UpdatePriority = "default"
    current_render_priority: UpdatePriority = "default"


__all__ = ["ReconcilerContainer"]

