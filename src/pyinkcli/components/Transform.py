from __future__ import annotations

from ..component import createElement


def Transform(*children, transform=None, **props):
    props = dict(props)
    if transform is not None:
        props["internal_transform"] = transform
    return createElement("ink-virtual-text", *children, **props)


__all__ = ["Transform"]

