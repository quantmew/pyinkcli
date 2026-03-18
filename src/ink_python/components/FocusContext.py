"""
Focus context placeholder to mirror JS file structure.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any


FocusContext: ContextVar[Any] = ContextVar("focus_context", default=None)

__all__ = ["FocusContext"]
