"""Process-exit cursor restore parity with JS cli-cursor/restore-cursor."""

from __future__ import annotations

import atexit
import sys

from ink_python.cursor_helpers import showCursorEscape

_registered = False


def _restore_cursor_on_exit() -> None:
    stream = sys.stderr
    is_tty = stream.isatty() if hasattr(stream, "isatty") else False
    if not is_tty:
        return

    try:
        writer = getattr(stream, "raw_write", None) or getattr(stream, "write", None)
        if callable(writer):
            writer(showCursorEscape)
            flush = getattr(stream, "flush", None)
            if callable(flush):
                flush()
    except Exception:
        pass


def ensureCursorRestoreRegistered() -> None:
    global _registered
    if _registered:
        return

    atexit.register(_restore_cursor_on_exit)
    _registered = True


__all__ = ["ensureCursorRestoreRegistered"]
