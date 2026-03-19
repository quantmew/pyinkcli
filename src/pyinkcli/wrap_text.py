"""
Wrap text for pyinkcli.

Wraps or truncates text based on available width.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pyinkcli.sanitize_ansi import sanitizeAnsi
from pyinkcli.packages.ink.styles import TextWrap
from pyinkcli.utils.wrap_ansi import wrap_ansi, truncate_string


@lru_cache(maxsize=1024)
def wrapText(
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

    sanitized = sanitizeAnsi(text)

    if wrap_type == "wrap":
        return wrap_ansi(sanitized, max_width, trim=False, hard=True)

    if wrap_type.startswith("truncate"):
        position: Literal["start", "middle", "end"] = "end"

        if wrap_type == "truncate-middle":
            position = "middle"
        elif wrap_type == "truncate-start":
            position = "start"

        return truncate_string(sanitized, max_width, position)

    return sanitized
