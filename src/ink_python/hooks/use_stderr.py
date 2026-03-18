"""
useStderr hook for ink-python.

Provides access to the stderr stream.
"""

from __future__ import annotations

import sys
from typing import Optional, TextIO

from ink_python.sanitize_ansi import sanitizeAnsi


class _StderrHandle:
    """Handle to stderr stream."""

    def __init__(self, stream: Optional[TextIO] = None):
        self._stream = stream or sys.stderr

    @property
    def stream(self) -> TextIO:
        """Get the underlying stream."""
        return self._stream

    @property
    def is_tty(self) -> bool:
        """Check if stderr is a TTY."""
        return self._stream.isatty() if hasattr(self._stream, "isatty") else False

    def write(self, data: str) -> None:
        """Write sanitized user output to stderr."""
        sanitized = sanitizeAnsi(data)
        self._stream.write(sanitized)
        self._stream.flush()

    def raw_write(self, data: str) -> None:
        """Write raw terminal control output to stderr."""
        self._stream.write(data)
        self._stream.flush()


# Global stderr handle
_stderr_handle: Optional[_StderrHandle] = None


def useStderr() -> _StderrHandle:
    """
    Hook to access stderr.

    Returns:
        StderrHandle with stream properties and methods.
    """
    global _stderr_handle
    if _stderr_handle is None:
        _stderr_handle = _StderrHandle()
    return _stderr_handle


def _set_stderr(stream: TextIO) -> None:
    """Internal: Set the stderr stream."""
    global _stderr_handle
    _stderr_handle = _StderrHandle(stream)
