"""JS-like hasOwnProperty helper."""

from __future__ import annotations

from typing import Any


def hasOwnProperty(target: Any, key: object) -> bool:
    return isinstance(target, dict) and key in target

