"""Synchronized output helpers matching JS `write-synchronized.ts`."""

from __future__ import annotations

import os
from typing import TextIO

bsu = "\u001b[?2026h"
esu = "\u001b[?2026l"


def shouldSynchronize(
    stream: TextIO,
    interactive: bool | None = None,
) -> bool:
    if not hasattr(stream, "isatty") or not stream.isatty():
        return False

    if interactive is not None:
        return interactive

    return os.environ.get("CI", "").lower() not in {"true", "1"}
