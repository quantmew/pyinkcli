from __future__ import annotations

from .sanitize_ansi import sanitizeAnsi
from .utils.string_width import widest_line


def measureText(text: str) -> tuple[int, int]:
    sanitized = sanitizeAnsi(text)
    lines = sanitized.splitlines() or [sanitized]
    return widest_line(sanitized), max(len(lines), 1)


__all__ = ["measureText"]

