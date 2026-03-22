"""Style types used by the Ink compatibility layer."""

from __future__ import annotations

from typing import Any, Literal

TextWrap = Literal[
    "wrap",
    "end",
    "middle",
    "truncate-end",
    "truncate",
    "truncate-middle",
    "truncate-start",
]
Styles = dict[str, Any]

__all__ = ["Styles"]

