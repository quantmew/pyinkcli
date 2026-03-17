"""
Spacer component for ink-python.

Creates flexible space between elements.
"""

from typing import Optional

from ink_python.component import VNode, create_vnode


def Spacer() -> VNode:
    """
    Spacer component - creates flexible space.

    Uses flexGrow: 1 to expand and fill available space.

    Returns:
        A VNode representing the spacer.
    """
    return create_vnode(
        "ink-box",
        style={
            "flexGrow": 1,
        },
    )
