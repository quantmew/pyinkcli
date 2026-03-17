"""
useStdin hook for ink-python.

Provides access to the stdin stream.
"""

from __future__ import annotations

import sys
from typing import Any, Optional, TextIO


class StdinHandle:
    """Handle to stdin stream."""

    def __init__(self, stream: Optional[TextIO] = None):
        self._stream = stream or sys.stdin
        self._raw_mode = False
        self._data_handlers: list[callable] = []

    @property
    def stream(self) -> TextIO:
        """Get the underlying stream."""
        return self._stream

    @property
    def is_tty(self) -> bool:
        """Check if stdin is a TTY."""
        return self._stream.isatty() if hasattr(self._stream, "isatty") else False

    @property
    def is_raw_mode_supported(self) -> bool:
        """Check if raw mode is supported."""
        return self.is_tty

    def set_raw_mode(self, enabled: bool) -> None:
        """
        Enable or disable raw mode.

        Args:
            enabled: Whether to enable raw mode.
        """
        if not self.is_raw_mode_supported:
            return

        try:
            import termios
            import tty

            if enabled and not self._raw_mode:
                self._old_settings = termios.tcgetattr(self._stream.fileno())
                tty.setraw(self._stream.fileno())
                self._raw_mode = True
            elif not enabled and self._raw_mode:
                if hasattr(self, "_old_settings"):
                    termios.tcsetattr(
                        self._stream.fileno(), termios.TCSADRAIN, self._old_settings
                    )
                self._raw_mode = False
        except Exception:
            pass

    def on_data(self, handler: callable) -> callable:
        """
        Register a data handler.

        Args:
            handler: Function to call when data is received.

        Returns:
            Unsubscribe function.
        """
        self._data_handlers.append(handler)
        return lambda: self._data_handlers.remove(handler)

    def read(self, size: int = -1) -> str:
        """Read from stdin."""
        return self._stream.read(size) if size > 0 else self._stream.read()

    def readline(self) -> str:
        """Read a line from stdin."""
        return self._stream.readline()


# Global stdin handle
_stdin_handle: Optional[StdinHandle] = None


def useStdin() -> StdinHandle:
    """
    Hook to access stdin.

    Returns:
        StdinHandle with stream properties and methods.
    """
    global _stdin_handle
    if _stdin_handle is None:
        _stdin_handle = StdinHandle()
    return _stdin_handle


def use_stdin() -> StdinHandle:
    """Alias for useStdin."""
    return useStdin()


def _set_stdin(stream: TextIO) -> None:
    """Internal: Set the stdin stream."""
    global _stdin_handle
    _stdin_handle = StdinHandle(stream)
