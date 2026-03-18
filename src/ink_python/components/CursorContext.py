"""
Cursor context placeholder to mirror JS file structure.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any


CursorContext: ContextVar[Any] = ContextVar("cursor_context", default=None)

__all__ = ["CursorContext"]
