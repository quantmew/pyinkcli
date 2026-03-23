from __future__ import annotations

bsu = "\x1b[?2026h"
esu = "\x1b[?2026l"


def shouldSynchronize(stream, interactive: bool | None = None) -> bool:
    is_tty = bool(getattr(stream, "isatty", lambda: False)())
    return is_tty and (True if interactive is None else interactive)


__all__ = ["bsu", "esu", "shouldSynchronize"]
