"""
useStdin hook for pyinkcli.

Provides access to the stdin stream.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from typing import Any, Callable, Optional, TextIO

from pyinkcli.components.StdinContext import _get_stdin


class _StdinHandle:
    """Handle to stdin stream."""

    def __init__(
        self,
        stream: Optional[TextIO] = None,
        output_stream: Optional[TextIO] = None,
    ):
        self._stream = stream or sys.stdin
        self._output_stream = output_stream or self._stream
        self._raw_mode = False
        self._data_handlers: list[callable] = []
        self._event_handlers: dict[str, list[Callable[..., None]]] = defaultdict(list)
        self._raw_mode_ref_count = 0
        self._bracketed_paste_mode = False
        self._bracketed_paste_ref_count = 0

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

            if enabled:
                self._raw_mode_ref_count += 1
                if not self._raw_mode:
                    self._old_settings = termios.tcgetattr(self._stream.fileno())
                    tty.setraw(self._stream.fileno())
                    self._raw_mode = True
            else:
                self._raw_mode_ref_count = max(0, self._raw_mode_ref_count - 1)
                if self._raw_mode and self._raw_mode_ref_count == 0:
                    if hasattr(self, "_old_settings"):
                        termios.tcsetattr(
                            self._stream.fileno(), termios.TCSADRAIN, self._old_settings
                        )
                    self._raw_mode = False
        except Exception:
            pass

    def set_bracketed_paste_mode(self, enabled: bool) -> None:
        """Enable or disable bracketed paste mode."""
        if enabled:
            self._bracketed_paste_ref_count += 1
            if self._bracketed_paste_mode:
                return
            self._bracketed_paste_mode = True
            self._write_terminal_mode("\x1b[?2004h")
            return

        self._bracketed_paste_ref_count = max(0, self._bracketed_paste_ref_count - 1)
        if self._bracketed_paste_ref_count == 0 and self._bracketed_paste_mode:
            self._bracketed_paste_mode = False
            self._write_terminal_mode("\x1b[?2004l")

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

    def on(self, event: str, handler: Callable[..., None]) -> Callable[[], None]:
        """Register an event handler."""

        self._event_handlers[event].append(handler)

        def unsubscribe() -> None:
            self.off(event, handler)

        return unsubscribe

    def off(self, event: str, handler: Callable[..., None]) -> None:
        """Remove an event handler."""

        handlers = self._event_handlers.get(event, [])
        try:
            handlers.remove(handler)
        except ValueError:
            pass

    def listener_count(self, event: str) -> int:
        """Return the number of listeners currently attached to an event."""
        return len(self._event_handlers.get(event, []))

    def clear_event_handlers(self, *events: str) -> None:
        """Clear registered handlers for one or more events."""
        target_events = events or tuple(self._event_handlers.keys())
        for event in target_events:
            self._event_handlers.pop(event, None)

    def emit(self, event: str, *args: Any) -> None:
        """Emit an event to registered handlers."""

        for handler in list(self._event_handlers.get(event, [])):
            try:
                handler(*args)
            except Exception:
                pass

    def cleanup_runtime_modes(self) -> None:
        """Restore terminal runtime modes managed by this handle."""

        while self._raw_mode_ref_count > 0:
            self.set_raw_mode(False)

        while self._bracketed_paste_ref_count > 0:
            self.set_bracketed_paste_mode(False)

    def _write_terminal_mode(self, data: str) -> None:
        if not hasattr(self._output_stream, "write"):
            return

        try:
            self._output_stream.write(data)
            if hasattr(self._output_stream, "flush"):
                self._output_stream.flush()
        except Exception:
            pass

    def read(self, size: int = -1) -> str:
        """Read from stdin."""
        return self._stream.read(size) if size > 0 else self._stream.read()

    def readline(self) -> str:
        """Read a line from stdin."""
        return self._stream.readline()


# Global stdin handle
_stdin_handle: Optional[_StdinHandle] = None


def useStdin() -> _StdinHandle:
    """
    Hook to access stdin.

    Returns:
        StdinHandle with stream properties and methods.
    """
    context_value = _get_stdin()
    if context_value is not None:
        return context_value

    global _stdin_handle
    if _stdin_handle is None:
        _stdin_handle = _StdinHandle()
    return _stdin_handle


def _set_stdin(stream: TextIO, output_stream: Optional[TextIO] = None) -> None:
    """Internal: Set the stdin stream."""
    global _stdin_handle
    _stdin_handle = _StdinHandle(stream, output_stream)
