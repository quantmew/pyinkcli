"""Python peer of JS `get-max-width.ts`."""

from __future__ import annotations

from pyinkcli import _yoga as yoga

__all__ = ["getMaxWidth"]


def getMaxWidth(yogaNode) -> float:
    """Return the maximum inner content width for a Yoga node."""
    return (
        yogaNode.get_computed_width()
        - yogaNode.get_computed_padding(yoga.EDGE_LEFT)
        - yogaNode.get_computed_padding(yoga.EDGE_RIGHT)
        - yogaNode.get_computed_border(yoga.EDGE_LEFT)
        - yogaNode.get_computed_border(yoga.EDGE_RIGHT)
    )
