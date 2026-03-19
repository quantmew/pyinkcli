from typing import Optional

from pyinkcli._component_runtime import createElement


def Spacer(size: int = 1) -> Optional[object]:
    if size <= 0:
        return None
    return createElement("ink-text", " " * size)


__all__ = ["Spacer"]
