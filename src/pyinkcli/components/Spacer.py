from __future__ import annotations

from ..component import createElement


def Spacer(**props):
    return createElement("ink-text", " ", **props)


__all__ = ["Spacer"]

