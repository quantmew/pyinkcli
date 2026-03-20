"""
Log update functionality for pyinkcli.

Provides standard and incremental terminal update modes.
"""

from __future__ import annotations

import sys
from typing import TextIO

from pyinkcli._restore_cursor import ensureCursorRestoreRegistered
from pyinkcli.cursor_helpers import (
    CursorPosition,
    buildCursorOnlySequence,
    buildCursorSuffix,
    buildReturnToBottomPrefix,
    cursorPositionChanged,
    hideCursorEscape,
    showCursorEscape,
)
from pyinkcli.utils.ansi_escapes import (
    cursor_next_line,
    cursor_to,
    cursor_up,
    erase_end_line,
    erase_lines,
)


def _visible_line_count(lines: list[str], output: str) -> int:
    return len(lines) - 1 if output.endswith("\n") else len(lines)


class LogUpdate:
    """
    Efficiently update terminal output.
    """

    def __init__(
        self,
        stream: TextIO,
        *,
        incremental: bool = False,
    ):
        self._stream = stream
        self._incremental = incremental
        self._previous_output = ""
        self._previous_lines: list[str] = []
        self._cursor_position: CursorPosition | None = None
        self._cursor_dirty = False
        self._previous_cursor_position: CursorPosition | None = None
        self._cursor_was_shown = False
        self._has_hidden_cursor = False

    def _is_tty(self) -> bool:
        return self._stream.isatty() if hasattr(self._stream, "isatty") else False

    def _prepare_payload(self, payload: str) -> str:
        is_tty = self._is_tty()
        if not is_tty or not payload:
            return payload

        # Do not rely on the terminal driver to translate LF into CRLF.
        # Some environments leave the cursor in the current column on `\n`,
        # which makes multi-line frames drift to the right.
        return payload.replace("\r\n", "\n").replace("\n", "\r\n")

    def __call__(self, output: str) -> bool:
        prefix = ""
        if self._is_tty() and not self._has_hidden_cursor:
            ensureCursorRestoreRegistered()
            prefix = hideCursorEscape
            self._has_hidden_cursor = True

        active_cursor = self._get_active_cursor()
        if not self._has_changes(output, active_cursor):
            return False

        payload = (
            self._render_incremental(output, active_cursor)
            if self._incremental
            else self._render_standard(output, active_cursor)
        )

        if payload:
            self._stream.write(self._prepare_payload(prefix + payload))
            self._stream.flush()

        self._previous_output = output
        self._previous_lines = output.split("\n")
        self._previous_cursor_position = (
            tuple(active_cursor) if active_cursor is not None else None
        )
        self._cursor_was_shown = active_cursor is not None
        return True

    def clear(self) -> None:
        prefix = buildReturnToBottomPrefix(
            self._cursor_was_shown,
            len(self._previous_lines),
            self._previous_cursor_position,
        )
        self._stream.write(
            self._prepare_payload(prefix + erase_lines(len(self._previous_lines)))
        )
        self._stream.flush()
        self._reset_previous()

    def done(self) -> None:
        if self._has_hidden_cursor:
            self._stream.write(self._prepare_payload(showCursorEscape))
            self._stream.flush()
            self._has_hidden_cursor = False
        self._reset_previous()

    def reset(self) -> None:
        self._reset_previous()

    def sync(self, output: str) -> None:
        active_cursor = self._get_active_cursor()
        lines = output.split("\n")
        self._previous_output = output
        self._previous_lines = lines

        if active_cursor is None and self._cursor_was_shown:
            self._stream.write(self._prepare_payload("\x1b[?25l"))
        elif active_cursor is not None:
            self._stream.write(
                self._prepare_payload(
                    buildCursorSuffix(_visible_line_count(lines, output), active_cursor)
                )
            )

        if active_cursor is not None or self._cursor_was_shown:
            self._stream.flush()

        self._previous_cursor_position = (
            tuple(active_cursor) if active_cursor is not None else None
        )
        self._cursor_was_shown = active_cursor is not None

    def set_cursor_position(self, position: CursorPosition | None) -> None:
        self._cursor_position = position
        self._cursor_dirty = True

    def is_cursor_dirty(self) -> bool:
        return self._cursor_dirty

    def will_render(self, output: str) -> bool:
        return self._has_changes(output, self._cursor_position if self._cursor_dirty else None)

    def _get_active_cursor(self) -> CursorPosition | None:
        active = self._cursor_position if self._cursor_dirty else None
        self._cursor_dirty = False
        return active

    def _has_changes(
        self,
        output: str,
        active_cursor: CursorPosition | None,
    ) -> bool:
        return output != self._previous_output or cursorPositionChanged(
            active_cursor,
            self._previous_cursor_position,
        )

    def _render_standard(
        self,
        output: str,
        active_cursor: CursorPosition | None,
    ) -> str:
        lines = output.split("\n")
        visible_count = _visible_line_count(lines, output)
        cursor_changed = cursorPositionChanged(
            active_cursor,
            self._previous_cursor_position,
        )

        if output == self._previous_output and cursor_changed:
            return buildCursorOnlySequence(
                cursor_was_shown=self._cursor_was_shown,
                previous_line_count=len(self._previous_lines),
                previous_cursor_position=self._previous_cursor_position,
                visible_line_count=visible_count,
                cursor_position=active_cursor,
            )

        return (
            buildReturnToBottomPrefix(
                self._cursor_was_shown,
                len(self._previous_lines),
                self._previous_cursor_position,
            )
            + erase_lines(len(self._previous_lines))
            + output
            + buildCursorSuffix(visible_count, active_cursor)
        )

    def _render_incremental(
        self,
        output: str,
        active_cursor: CursorPosition | None,
    ) -> str:
        next_lines = output.split("\n")
        visible_count = _visible_line_count(next_lines, output)
        previous_visible = _visible_line_count(self._previous_lines, self._previous_output)
        cursor_changed = cursorPositionChanged(
            active_cursor,
            self._previous_cursor_position,
        )

        if output == self._previous_output and cursor_changed:
            return buildCursorOnlySequence(
                cursor_was_shown=self._cursor_was_shown,
                previous_line_count=len(self._previous_lines),
                previous_cursor_position=self._previous_cursor_position,
                visible_line_count=visible_count,
                cursor_position=active_cursor,
            )

        return_prefix = buildReturnToBottomPrefix(
            self._cursor_was_shown,
            len(self._previous_lines),
            self._previous_cursor_position,
        )

        if output == "\n" or self._previous_output == "":
            return (
                return_prefix
                + erase_lines(len(self._previous_lines))
                + output
                + buildCursorSuffix(visible_count, active_cursor)
            )

        has_trailing_newline = output.endswith("\n")
        buffer: list[str] = [return_prefix]

        if visible_count < previous_visible:
            previous_had_trailing_newline = self._previous_output.endswith("\n")
            extra_slot = 1 if previous_had_trailing_newline else 0
            buffer.append(erase_lines(previous_visible - visible_count + extra_slot))
            if visible_count > 0:
                buffer.append(cursor_up(visible_count))
        elif previous_visible > 0:
            buffer.append(cursor_up(previous_visible - 1))

        for index in range(visible_count):
            is_last_line = index == visible_count - 1
            next_line = next_lines[index]
            previous_line = self._previous_lines[index] if index < len(self._previous_lines) else None

            if next_line == previous_line:
                if not is_last_line or has_trailing_newline:
                    buffer.append(cursor_next_line())
                continue

            buffer.append(
                cursor_to(0)
                + next_line
                + erase_end_line()
                + ("" if is_last_line and not has_trailing_newline else "\n")
            )

        buffer.append(buildCursorSuffix(visible_count, active_cursor))
        return "".join(buffer)

    def _reset_previous(self) -> None:
        self._previous_output = ""
        self._previous_lines = []
        self._previous_cursor_position = None
        self._cursor_was_shown = False


def _createLogUpdate(
    stream: TextIO | None = None,
    *,
    incremental: bool = False,
) -> LogUpdate:
    return LogUpdate(stream or sys.stdout, incremental=incremental)


def logUpdate(
    stream: TextIO | None = None,
    *,
    incremental: bool = False,
) -> LogUpdate:
    return _createLogUpdate(stream, incremental=incremental)


__all__ = ["LogUpdate", "logUpdate"]
