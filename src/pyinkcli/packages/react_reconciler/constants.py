"""Semi-public reconciler constants."""

from __future__ import annotations

from .ReactEventPriorities import (
    ContinuousEventPriority,
    DefaultEventPriority,
    DiscreteEventPriority,
    IdleEventPriority,
    NoEventPriority,
)
from .ReactRootTags import ConcurrentRoot, LegacyRoot

priorityRank = {
    NoEventPriority: 0,
    IdleEventPriority: 1,
    DefaultEventPriority: 2,
    ContinuousEventPriority: 3,
    DiscreteEventPriority: 4,
}

__all__ = [
    "NoEventPriority",
    "DiscreteEventPriority",
    "ContinuousEventPriority",
    "DefaultEventPriority",
    "IdleEventPriority",
    "priorityRank",
    "ConcurrentRoot",
    "LegacyRoot",
]
