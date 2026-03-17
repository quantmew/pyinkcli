"""
Transform component for ink-python.

Applies transformations to child output.
"""

from typing import Any, Callable, Optional, Union

from ink_python.component import VNode, create_vnode


def Transform(
    *children: Union[VNode, str, None],
    transform: Callable[[str], str],
) -> Optional[VNode]:
    """
    Transform component - applies transformations to output.

    Args:
        *children: Child components.
        transform: Function to transform the output string.

    Returns:
        A VNode with the transform applied.
    """
    if not children:
        return None

    # Create a wrapper transform that handles the index parameter
    def internal_transform(s: str, index: int) -> str:
        return transform(s)

    return create_vnode(
        "ink-box",
        *children,
        internal_transform=internal_transform,
    )
