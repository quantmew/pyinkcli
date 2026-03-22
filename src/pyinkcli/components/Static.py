from __future__ import annotations

from ..component import createElement


def Static(*children, **props):
    props = dict(props)
    props["internal_static"] = True
    return createElement("ink-box", *children, **props)


__all__ = ["Static"]

