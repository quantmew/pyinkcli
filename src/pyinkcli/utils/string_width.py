from __future__ import annotations

from wcwidth import wcswidth

from ..sanitize_ansi import sanitizeAnsi


def string_width(value: str, *, count_ansi_escape_codes: bool = False) -> int:
    if not isinstance(value, str) or not value:
        return 0
    text = value if count_ansi_escape_codes else sanitizeAnsi(value)
    text = text.replace("\n", "")
    width = wcswidth(text)
    return max(width, 0)


def widest_line(value: str) -> int:
    if not value:
        return 0
    return max(string_width(line) for line in value.split("\n"))


__all__ = ["string_width", "widest_line"]

