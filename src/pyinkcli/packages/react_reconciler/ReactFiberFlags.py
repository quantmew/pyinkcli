"""Minimal fiber flag surface aligned with React commit phases."""

from __future__ import annotations

NoFlags = 0
Placement = 1 << 0
Update = 1 << 1
Deletion = 1 << 2
Ref = 1 << 3
Passive = 1 << 4
Callback = 1 << 5
Insertion = 1 << 6

MutationMask = Placement | Update | Deletion | Ref | Insertion
LayoutMask = Ref | Callback
PassiveMask = Passive

__all__ = [
    "NoFlags",
    "Placement",
    "Update",
    "Deletion",
    "Ref",
    "Passive",
    "Callback",
    "Insertion",
    "MutationMask",
    "LayoutMask",
    "PassiveMask",
]
