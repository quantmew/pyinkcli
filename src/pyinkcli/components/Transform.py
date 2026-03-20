from __future__ import annotations

from collections.abc import Callable

from pyinkcli._component_runtime import RenderableNode, createElement


def Transform(
    *children: RenderableNode,
    transform: Callable[[str, int], str],
) -> RenderableNode:
    return createElement("ink-box", *children, internal_transform=transform)


__all__ = ["Transform"]
