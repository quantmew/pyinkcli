from __future__ import annotations

from types import SimpleNamespace


def measureElement(node):
    return SimpleNamespace(
        width=getattr(node, "computed_width", getattr(node, "width", 0)) or 0,
        height=getattr(node, "computed_height", getattr(node, "height", 0)) or 0,
    )


__all__ = ["measureElement"]

