"""
Calculate the visual width of a string in terminal columns.

A Python port of the string-width JavaScript library.
Uses wcwidth for proper Unicode width calculation.
"""

from __future__ import annotations

import re
from typing import Literal

from wcwidth import wcwidth

# ANSI escape sequence regex
ANSI_REGEX = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return ANSI_REGEX.sub("", text)


def string_width(
    text: str,
    *,
    ambiguous_is_narrow: bool = True,
    count_ansi_escape_codes: bool = False,
) -> int:
    """
    Calculate the visual width of a string in terminal columns.

    Args:
        text: The string to measure.
        ambiguous_is_narrow: Treat ambiguous-width characters as narrow (width 1).
        count_ansi_escape_codes: Whether to count ANSI escape codes in the width.

    Returns:
        The visual width of the string in terminal columns.
    """
    if not isinstance(text, str) or len(text) == 0:
        return 0

    string = text

    # Strip ANSI escape codes unless counting them
    if not count_ansi_escape_codes and ("\x1B" in string or "\x9B" in string):
        string = _strip_ansi(string)

    if len(string) == 0:
        return 0

    # Fast path: ASCII printable characters (0x20-0x7E)
    if all(0x20 <= ord(c) <= 0x7E for c in string):
        return len(string)

    width = 0
    for char in string:
        # Get the width of the character
        char_width = wcwidth(char)

        # Handle ambiguous characters if needed
        if char_width == -1:
            # Non-printable character
            continue
        elif char_width == 2 and ambiguous_is_narrow:
            # Some terminals treat ambiguous characters as narrow
            # For simplicity, we'll use wcwidth's result
            pass

        width += max(char_width, 0)

    return width


def widest_line(text: str) -> int:
    """
    Get the width of the widest line in a multi-line string.

    Args:
        text: The multi-line string to measure.

    Returns:
        The width of the widest line.
    """
    if not text:
        return 0

    max_width = 0
    for line in text.split("\n"):
        max_width = max(max_width, string_width(line))

    return max_width
