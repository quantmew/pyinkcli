"""forwardRef helpers aligned with ReactForwardRef."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

@dataclass
class ReactForwardRefType:
    render: Callable[[dict[str, Any], Any], Any]
    __ink_react_forward_ref__: bool = True


def forwardRef(render: Callable[[dict[str, Any], Any], Any]) -> ReactForwardRefType:
    return ReactForwardRefType(render=render)


__all__ = ["ReactForwardRefType", "forwardRef"]
