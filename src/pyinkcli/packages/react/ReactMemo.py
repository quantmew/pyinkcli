"""React.memo compatibility helper."""

from __future__ import annotations

from typing import Any

from pyinkcli._component_runtime import renderComponent
from pyinkcli.packages.shared.ReactSymbols import REACT_MEMO_TYPE


class _MemoType:
    def __init__(self, inner_type: Any, compare=None) -> None:
        self.__dict__["$$typeof"] = REACT_MEMO_TYPE
        self.type = inner_type
        self.compare = compare
        self.displayName = None
        self.__ink_react_memo__ = True

    def __call__(self, *children, **props):
        return renderComponent(self.type, *children, **props)


def memo(inner_type, compare=None):
    return _MemoType(inner_type, compare)


__all__ = ["memo"]
