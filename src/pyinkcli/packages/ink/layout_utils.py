"""Shared helpers for safely consuming Yoga computed layout values."""

from __future__ import annotations

import math
from typing import Any


def safe_layout_number(value: float) -> float | None:
    if not math.isfinite(value):
        return None
    return value


def safe_layout_int(value: float) -> int | None:
    number = safe_layout_number(value)
    if number is None:
        return None
    return int(number)


def safe_yoga_int(node: Any, getter_name: str) -> int | None:
    yoga_node = getattr(node, "yogaNode", None)
    if yoga_node is None:
        return None
    getter = getattr(yoga_node, getter_name, None)
    if not callable(getter):
        return None
    return safe_layout_int(getter())

