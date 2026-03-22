from __future__ import annotations

from .utils.wrap_ansi import wrap_ansi


def wrapText(text: str, columns: int) -> str:
    return wrap_ansi(text, columns, hard=True)


__all__ = ["wrapText"]

