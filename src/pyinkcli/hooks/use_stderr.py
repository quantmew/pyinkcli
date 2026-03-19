"""
useStderr hook for pyinkcli.

Provides access to the stderr stream and Ink-preserving writes.
"""

from __future__ import annotations

import sys
from typing import Callable, Optional, TextIO

from pyinkcli.components.StderrContext import _get_stderr
from pyinkcli.sanitize_ansi import sanitizeAnsi


class _StderrHandle:
    """Handle to stderr stream."""

    def __init__(self, stream: Optional[TextIO] = None):
        self._stream = stream or sys.stderr
        self._overlay_writer: Optional[Callable[[str], None]] = None

    @property
    def stream(self) -> TextIO:
        """Get the underlying stream."""
        return self._stream

    @property
    def stderr(self) -> TextIO:
        """Get the underlying stderr stream for JS Ink parity."""
        return self._stream

    @property
    def is_tty(self) -> bool:
        """Check if stderr is a TTY."""
        return self._stream.isatty() if hasattr(self._stream, "isatty") else False

    def bind_overlay_writer(self, writer: Optional[Callable[[str], None]]) -> None:
        """Route write() through the Ink overlay writer when available."""
        self._overlay_writer = writer

    def _prepare_payload(self, data: str) -> str:
        if not self.is_tty or not data:
            return data

        return data.replace("\r\n", "\n").replace("\n", "\r\n")

    def write(self, data: str) -> None:
        """Write sanitized user output while preserving Ink output when possible."""
        sanitized = sanitizeAnsi(data)
        if self._overlay_writer is not None:
            self._overlay_writer(sanitized)
            return

        self._stream.write(self._prepare_payload(sanitized))
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
    context_value = _get_stderr()
    if context_value is not None:
        return context_value

    global _stderr_handle
    if _stderr_handle is None:
        _stderr_handle = _StderrHandle()
    return _stderr_handle


def _set_stderr(stream: TextIO) -> None:
    """Internal: Set the stderr stream."""
    global _stderr_handle
    _stderr_handle = _StderrHandle(stream)
