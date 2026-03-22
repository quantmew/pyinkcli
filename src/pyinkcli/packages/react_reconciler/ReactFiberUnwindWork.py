"""Unwind helpers aligned with ReactFiberUnwindWork responsibilities."""

from __future__ import annotations

from typing import Any

def unwindInterruptedWork(fiber: Any) -> None:
    del fiber


__all__ = ["unwindInterruptedWork"]
