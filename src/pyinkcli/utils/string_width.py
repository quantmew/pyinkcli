from __future__ import annotations

from functools import lru_cache

from wcwidth import wcswidth

from ..ansi_tokenizer import tokenizeAnsi


def _strip_ansi(value: str) -> str:
    if "\x1b" not in value:
        return value
    return "".join(token.value for token in tokenizeAnsi(value) if token.type == "text")


@lru_cache(maxsize=8192)
def _string_width_cached(value: str, count_ansi_escape_codes: bool) -> int:
    if not isinstance(value, str) or not value:
        return 0
    text = value if count_ansi_escape_codes else _strip_ansi(value)
    text = text.replace("\n", "")
    width = wcswidth(text)
    return max(width, 0)


def string_width(value: str, *, count_ansi_escape_codes: bool = False) -> int:
    return _string_width_cached(value, count_ansi_escape_codes)


def widest_line(value: str) -> int:
    if not value:
        return 0
    return max(string_width(line) for line in value.split("\n"))


__all__ = ["string_width", "widest_line"]
