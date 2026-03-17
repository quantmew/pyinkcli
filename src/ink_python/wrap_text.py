"""
Wrap text for ink-python.

Wraps or truncates text based on available width.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from ink_python.styles import TextWrap
from ink_python.utils.wrap_ansi import wrap_ansi, truncate_string


@lru_cache(maxsize=1024)
def wrap_text(
    text: str,
    max_width: int,
    wrap_type: TextWrap = "wrap",
) -> str:
    """
    Wrap or truncate text based on the wrap type.

    Args:
        text: The text to wrap.
        max_width: The maximum width in columns.
        wrap_type: How to handle text overflow.

    Returns:
        The wrapped or truncated text.
    """
    if not text:
        return ""

    if wrap_type == "wrap":
        return wrap_ansi(text, max_width, trim=False, hard=True)

    if wrap_type.startswith("truncate"):
        position: Literal["start", "middle", "end"] = "end"

        if wrap_type == "truncate-middle":
            position = "middle"
        elif wrap_type == "truncate-start":
            position = "start"

        return truncate_string(text, max_width, position)

    return text
