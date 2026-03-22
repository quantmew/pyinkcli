"""Array predicate helper."""

from __future__ import annotations

from typing import Any


def isArray(value: Any) -> bool:
    return isinstance(value, list)

