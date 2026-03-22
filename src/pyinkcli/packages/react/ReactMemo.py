"""Memo helpers aligned with ReactMemo."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

@dataclass
class ReactMemoType:
    type: Callable[..., Any]
    compare: Callable[[Any, Any], bool] | None = None
    __ink_react_memo__: bool = True


def memo(type: Callable[..., Any], compare: Callable[[Any, Any], bool] | None = None) -> ReactMemoType:
    return ReactMemoType(type=type, compare=compare)


__all__ = ["ReactMemoType", "memo"]
