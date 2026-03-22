"""React.forwardRef compatibility helper."""

from __future__ import annotations

from typing import Any

from pyinkcli.packages.shared.ReactSymbols import REACT_FORWARD_REF_TYPE, REACT_MEMO_TYPE


class _ForwardRefType:
    def __init__(self, render) -> None:
        self.__dict__["$$typeof"] = REACT_FORWARD_REF_TYPE
        self.render = render
        self.displayName = None
        self.__ink_react_forward_ref__ = True

    def __call__(self, *children, **props):
        ref = props.pop("ref", None)
        if children:
            props = dict(props)
            props.setdefault("children", children[0] if len(children) == 1 else list(children))
        return self.render(props, ref)


def forwardRef(render):
    if render is not None and getattr(render, "$$typeof", None) is REACT_MEMO_TYPE:
        raise TypeError(
            "forwardRef requires a render function but received a memo component."
        )
    return _ForwardRefType(render)


__all__ = ["forwardRef"]
