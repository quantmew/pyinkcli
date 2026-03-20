"""
Measure text dimensions for pyinkcli.

Calculates the visual dimensions of text in terminal columns and rows.
"""

from __future__ import annotations

from functools import lru_cache

from pyinkcli.sanitize_ansi import sanitizeAnsi
from pyinkcli.utils.string_width import widest_line


@lru_cache(maxsize=1024)
def measureText(text: str) -> tuple[int, int]:
    """
    Measure the dimensions of text.

    Args:
        text: The text to measure.

    Returns:
        A tuple of (width, height) in terminal units.
    """
    if not text or len(text) == 0:
        return (0, 0)

    sanitized = sanitizeAnsi(text)
    width = widest_line(sanitized)
    height = sanitized.count("\n") + 1 if sanitized else 0

    return (width, height)
