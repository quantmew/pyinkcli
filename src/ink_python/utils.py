"""Utility helpers matching JS `utils.ts`."""

from __future__ import annotations

import shutil
from typing import TextIO


def getWindowSize(stdout: TextIO) -> dict[str, int]:
    columns = getattr(stdout, "columns", None) or 0
    rows = getattr(stdout, "rows", None) or 0

    if columns and rows:
        return {"columns": columns, "rows": rows}

    try:
        fallback = shutil.get_terminal_size()
        return {
            "columns": columns or fallback.columns or 80,
            "rows": rows or fallback.lines or 24,
        }
    except Exception:
        return {"columns": columns or 80, "rows": rows or 24}
