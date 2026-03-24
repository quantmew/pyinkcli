from __future__ import annotations

from ..sanitize_ansi import sanitizeAnsi
from ..utils.string_width import string_width


def wrap_ansi(text: str, columns: int, *, hard: bool = False) -> str:
    sanitized = sanitizeAnsi(text)
    if not hard:
        words = sanitized.split(" ")
        wrapped_lines: list[str] = []
        current = ""
        for _index, word in enumerate(words):
            candidate = word if not current else current + " " + word
            if string_width(candidate) <= columns or not current:
                current = candidate
                continue
            wrapped_lines.append(current)
            current = word
        if current or not wrapped_lines:
            wrapped_lines.append(current)
        return "\n".join(wrapped_lines)
    lines: list[str] = []
    current = ""
    for character in sanitized:
        if character == "\n":
            lines.append(current)
            current = ""
            continue
        if string_width(current + character) > columns and current:
            lines.append(current)
            current = character
        else:
            current += character
    if current or not lines:
        lines.append(current)
    return "\n".join(lines)


def truncate_string(text: str, columns: int, position: str = "end") -> str:
    sanitized = sanitizeAnsi(text)
    current = ""
    for character in sanitized:
        if string_width(current + character) > columns:
            break
        current += character
    return current


__all__ = ["truncate_string", "wrap_ansi"]
