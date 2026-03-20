"""
useStdout hook for pyinkcli.

Provides access to the stdout stream and Ink-preserving writes.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import TextIO

from pyinkcli.components.StdoutContext import _get_stdout
from pyinkcli.sanitize_ansi import sanitizeAnsi


class _StdoutHandle:
    """Handle to stdout stream."""

    def __init__(self, stream: TextIO | None = None):
        self._stream = stream or sys.stdout
        self._overlay_writer: Callable[[str], None] | None = None
        self._resize_handlers: list[Callable[[], None]] = []

    @property
    def stream(self) -> TextIO:
        """Get the underlying stream."""
        return self._stream

    @property
    def stdout(self) -> TextIO:
        """Get the underlying stdout stream for JS Ink parity."""
        return self._stream

    @property
    def columns(self) -> int:
        """Get the number of columns in the terminal."""
        stream_columns = getattr(self._stream, "columns", None)
        if isinstance(stream_columns, int) and stream_columns > 0:
            return stream_columns

        try:
            import shutil
            size = shutil.get_terminal_size()
            return size.columns
        except Exception:
            return 80

    @property
    def rows(self) -> int:
        """Get the number of rows in the terminal."""
        stream_rows = getattr(self._stream, "rows", None)
        if isinstance(stream_rows, int) and stream_rows > 0:
            return stream_rows

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

    def bind_overlay_writer(self, writer: Callable[[str], None] | None) -> None:
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
        """Write raw terminal control output to stdout."""
        self._stream.write(data)
        self._stream.flush()

    def on_resize(self, handler: Callable[[], None]) -> Callable[[], None]:
        """
        Register a resize handler.

        Args:
            handler: Function to call on terminal resize.

        Returns:
            Unsubscribe function.
        """
        self._resize_handlers.append(handler)

        def unsubscribe() -> None:
            if handler in self._resize_handlers:
                self._resize_handlers.remove(handler)

        return unsubscribe

    def emit_resize(self) -> None:
        """Notify registered resize listeners."""
        for handler in list(self._resize_handlers):
            handler()


# Global stdout handle
_stdout_handle: _StdoutHandle | None = None


def useStdout() -> _StdoutHandle:
    """
    Hook to access stdout.

    Returns:
        StdoutHandle with stream properties and methods.
    """
    context_value = _get_stdout()
    if context_value is not None:
        return context_value

    global _stdout_handle
    if _stdout_handle is None:
        _stdout_handle = _StdoutHandle()
    return _stdout_handle


def _set_stdout(stream: TextIO) -> None:
    """Internal: Set the stdout stream."""
    global _stdout_handle
    _stdout_handle = _StdoutHandle(stream)


def _emit_stdout_resize() -> None:
    """Internal: notify resize listeners on the current stdout handle."""
    if _stdout_handle is not None:
        _stdout_handle.emit_resize()
