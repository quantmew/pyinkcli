from __future__ import annotations

from ..component import createElement


def App(*children, **props):
    return createElement("ink-box", *children, **props)


__all__ = ["App"]
