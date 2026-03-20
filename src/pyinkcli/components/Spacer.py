
from __future__ import annotations

from pyinkcli._component_runtime import createElement


def Spacer(size: int = 1) -> object | None:
    if size <= 0:
        return None
    return createElement("ink-text", " " * size)


__all__ = ["Spacer"]
