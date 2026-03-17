"""
Static component for ink-python.

Renders content only once and never updates it.
"""

from typing import Any, Optional, Union

from ink_python.component import VNode, create_vnode


def Static(
    *children: Union[VNode, str, None],
    items: Optional[list[Any]] = None,
    style: Optional[dict[str, Any]] = None,
) -> Optional[VNode]:
    """
    Static component - renders content only once.

    Useful for output that should persist and not be re-rendered
    when the rest of the UI updates.

    Args:
        *children: Child components.
        items: Optional list of items to render statically.
        style: Optional style properties.

    Returns:
        A VNode representing the static content.
    """
    content: list[Union[VNode, str, None]] = []

    if items is not None:
        for item in items:
            if isinstance(item, str):
                content.append(create_vnode("ink-text", item))
            elif isinstance(item, VNode):
                content.append(item)
            else:
                content.append(create_vnode("ink-text", str(item)))
    else:
        content.extend(children)

    if not content:
        return None

    return create_vnode(
        "ink-box",
        *content,
        style=style or {},
        internal_static=True,
    )
