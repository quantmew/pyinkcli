from __future__ import annotations

from ..component import createElement


def Newline(**props):
    return createElement("ink-text", "\n", **props)


__all__ = ["Newline"]

