from __future__ import annotations

from contextlib import contextmanager

_screen_reader_enabled = False


@contextmanager
def _provide_accessibility(enabled: bool):
    global _screen_reader_enabled
    previous = _screen_reader_enabled
    _screen_reader_enabled = enabled
    try:
        yield enabled
    finally:
        _screen_reader_enabled = previous

