"""
Log update functionality for ink-python.

Handles updating terminal output efficiently.
"""

from __future__ import annotations

import sys
from typing import Optional, TextIO


class LogUpdate:
    """
    Efficiently update terminal output.

    Similar to the log-update JavaScript library.
    """

    def __init__(
        self,
        stream: TextIO,
        *,
        incremental: bool = False,
    ):
        """
        Initialize LogUpdate.

        Args:
            stream: The output stream (usually stdout).
            incremental: Whether to use incremental rendering.
        """
        self._stream = stream
        self._incremental = incremental
        self._previous_output: Optional[str] = None
        self._cursor_x = 0
        self._cursor_y = 0

    def __call__(self, output: str) -> None:
        """
        Update the output.

        Args:
            output: The new output string.
        """
        if self._previous_output == output:
            return

        if self._previous_output is not None:
            self._clear_previous()

        self._stream.write(output)
        self._stream.flush()
        self._previous_output = output
        self._cursor_x = 0
        self._cursor_y = output.count("\n")

    def clear(self) -> None:
        """Clear the current output."""
        if self._previous_output is None:
            return

        self._clear_previous()
        self._previous_output = None

    def done(self) -> None:
        """Finalize the output (keep it on screen)."""
        if self._previous_output is not None:
            self._stream.write("\n")
            self._stream.flush()
        self._previous_output = None

    def sync(self, output: str) -> None:
        """
        Sync the internal state with an output string.

        Args:
            output: The output to sync with.
        """
        self._previous_output = output
        self._cursor_y = output.count("\n")

    def will_render(self, output: str) -> bool:
        """
        Check if the output will actually render.

        Args:
            output: The output to check.

        Returns:
            True if the output will be rendered.
        """
        return output != self._previous_output

    def set_cursor_position(self, position: Optional[tuple[int, int]]) -> None:
        """
        Set the cursor position for rendering.

        Args:
            position: Tuple of (x, y) position.
        """
        if position:
            self._cursor_x, self._cursor_y = position

    def _clear_previous(self) -> None:
        """Clear the previous output."""
        if self._previous_output is None:
            return

        lines = self._previous_output.count("\n") + 1

        # Move cursor to start of previous output
        if self._cursor_y > 0:
            self._stream.write(f"\x1b[{self._cursor_y}A")

        # Clear lines
        for i in range(lines):
            if i > 0:
                self._stream.write("\x1b[1B")  # Move down
            self._stream.write("\x1b[2K\x1b[G")  # Clear line and go to start

        self._stream.flush()


def create_log_update(
    stream: Optional[TextIO] = None,
    *,
    incremental: bool = False,
) -> LogUpdate:
    """
    Create a LogUpdate instance.

    Args:
        stream: The output stream (defaults to stdout).
        incremental: Whether to use incremental rendering.

    Returns:
        A LogUpdate instance.
    """
    return LogUpdate(stream or sys.stdout, incremental=incremental)
