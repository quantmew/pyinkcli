"""Hook effect flag constants."""

from __future__ import annotations

NoFlags = 0
HasEffect = 1 << 0
Insertion = 1 << 1
Layout = 1 << 2
Passive = 1 << 3

__all__ = ["NoFlags", "HasEffect", "Insertion", "Layout", "Passive"]

