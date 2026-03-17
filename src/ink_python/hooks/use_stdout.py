"""
useStdout hook for ink-python.

Provides access to the stdout stream.
"""

from __future__ import annotations

import sys
from typing import Any, Optional, TextIO


class StdoutHandle:
    """Handle to stdout stream."""

    def __init__(self, stream: Optional[TextIO] = None):
        self._stream = stream or sys.stdout
        self._write_handlers: list[callable] = []

    @property
    def stream(self) -> TextIO:
        """Get the underlying stream."""
        return self._stream

    @property
    def columns(self) -> int:
        """Get the number of columns in the terminal."""
        try:
            import shutil
            size = shutil.get_terminal_size()
            return size.columns
        except Exception:
            return 80

    @property
    def rows(self) -> int:
        """Get the number of rows in the terminal."""
        try:
            import shutil
            size = shutil.get_terminal_size()
            return size.lines
        except Exception:
            return 24

    @property
    def is_tty(self) -> bool:
        """Check if stdout is a TTY."""
        return self._stream.isatty() if hasattr(self._stream, "isatty") else False

    def write(self, data: str) -> None:
        """Write to stdout."""
        self._stream.write(data)
        self._stream.flush()

    def on_resize(self, handler: callable) -> callable:
        """
        Register a resize handler.

        Args:
            handler: Function to call on terminal resize.

        Returns:
            Unsubscribe function.
        """
        self._write_handlers.append(handler)
        return lambda: self._write_handlers.remove(handler)


# Global stdout handle
_stdout_handle: Optional[StdoutHandle] = None


def useStdout() -> StdoutHandle:
    """
    Hook to access stdout.

    Returns:
        StdoutHandle with stream properties and methods.
    """
    global _stdout_handle
    if _stdout_handle is None:
        _stdout_handle = StdoutHandle()
    return _stdout_handle


def use_stdout() -> StdoutHandle:
    """Alias for useStdout."""
    return useStdout()


def _set_stdout(stream: TextIO) -> None:
    """Internal: Set the stdout stream."""
    global _stdout_handle
    _stdout_handle = StdoutHandle(stream)
