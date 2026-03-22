"""`Object.assign` style helper."""

from __future__ import annotations

from typing import Any


def assign(target: dict[str, Any], *sources: object) -> dict[str, Any]:
    for source in sources:
        if isinstance(source, dict):
            target.update(source)
    return target

