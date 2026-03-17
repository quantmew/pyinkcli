"""
Newline component for ink-python.

Inserts line breaks.
"""

from typing import Optional

from ink_python.component import VNode, create_vnode


def Newline(count: int = 1) -> VNode:
    """
    Newline component - inserts line breaks.

    Args:
        count: Number of newlines to insert.

    Returns:
        A VNode representing the newlines.
    """
    if count < 1:
        count = 1
    return create_vnode("ink-text", "\n" * count)
