from __future__ import annotations

from .yoga_compat import EDGE_LEFT, EDGE_RIGHT


def getMaxWidth(yoga_node) -> int:
    return (
        int(yoga_node.get_computed_width())
        - int(yoga_node.get_computed_padding(EDGE_LEFT))
        - int(yoga_node.get_computed_padding(EDGE_RIGHT))
        - int(yoga_node.get_computed_border(EDGE_LEFT))
        - int(yoga_node.get_computed_border(EDGE_RIGHT))
    )


__all__ = ["getMaxWidth"]

