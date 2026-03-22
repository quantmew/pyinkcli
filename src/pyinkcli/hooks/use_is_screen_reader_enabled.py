from __future__ import annotations

_enabled = False


def _set_screen_reader_enabled(enabled: bool) -> None:
    global _enabled
    _enabled = enabled


def useIsScreenReaderEnabled() -> bool:
    return _enabled


__all__ = ["useIsScreenReaderEnabled", "_set_screen_reader_enabled"]

