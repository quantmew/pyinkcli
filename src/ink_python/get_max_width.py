"""
Get maximum width from a Yoga node.

Utility function to calculate the maximum content width.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ink_python import yoga_compat as yoga


def get_max_width(yoga_node: "yoga.Node") -> int:
    """
    Get the maximum content width for a Yoga node.

    Args:
        yoga_node: The Yoga node.

    Returns:
        The maximum content width in columns.
    """
    from ink_python import yoga_compat as yoga

    width = yoga_node.get_computed_width()
    padding_left = yoga_node.get_computed_padding(yoga.EDGE_LEFT)
    padding_right = yoga_node.get_computed_padding(yoga.EDGE_RIGHT)
    border_left = yoga_node.get_computed_border(yoga.EDGE_LEFT)
    border_right = yoga_node.get_computed_border(yoga.EDGE_RIGHT)

    return int(width - padding_left - padding_right - border_left - border_right)
