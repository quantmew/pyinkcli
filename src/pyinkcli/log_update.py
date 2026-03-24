from __future__ import annotations

import os

from .cursor_helpers import (
    buildCursorOnlySequence,
    buildCursorSuffix,
    buildReturnToBottom,
    buildReturnToBottomPrefix,
)
from .output import Output
from .utils.ansi_escapes import (
    cursor_left,
    cursor_next_line,
    cursor_up,
    erase_line,
    erase_lines,
    hide_cursor_escape,
    show_cursor_escape,
)
from .utils.string_width import string_width


class LogUpdate:
    def __init__(self, stream, incremental: bool = False) -> None:
        self.stream = stream
        self.incremental = incremental
        self.previous_output: str | None = None
        self.previous_line_count = 0
        self.cursor_position = None
        self._cursor_position = (0, 0)
        self.previous_cursor_position = None
        self.cursor_was_shown = False

    def set_cursor_position(self, position) -> None:
        self.cursor_position = position
        self._cursor_position = position

    def _normalize(self, text: str) -> str:
        if hasattr(self.stream, "isatty") and self.stream.isatty():
            return text.replace("\n", "\r\n")
        return text

    def _terminal_columns(self) -> int:
        columns = getattr(self.stream, "columns", None)
        if isinstance(columns, int) and columns > 0:
            return columns
        if hasattr(self.stream, "isatty") and self.stream.isatty() and hasattr(self.stream, "fileno"):
            try:
                return os.get_terminal_size(self.stream.fileno()).columns or 80
            except OSError:
                pass
        return 80

    def _visual_rows(self, text: str) -> list[str]:
        if text == "":
            return []

        columns = max(self._terminal_columns(), 1)
        rows: list[str] = []

        for logical_line in text.split("\n"):
            cells = Output._styled_cells(logical_line)
            if not cells:
                rows.append("")
                continue

            current_row = []
            current_width = 0

            for cell in cells:
                cell_width = max(string_width(cell.char), 1)
                if current_row and current_width + cell_width > columns:
                    rows.append(Output._styled_cells_to_string(current_row))
                    current_row = []
                    current_width = 0

                current_row.append(cell)
                current_width += cell_width

                if current_width >= columns:
                    rows.append(Output._styled_cells_to_string(current_row))
                    current_row = []
                    current_width = 0

            if current_row:
                rows.append(Output._styled_cells_to_string(current_row))

        return rows

    def _visible_line_count(self, text: str) -> int:
        return len(self._visual_rows(text))

    def _return_to_top_prefix(self) -> str:
        if self.previous_line_count <= 0:
            return hide_cursor_escape if self.cursor_was_shown else ""

        output = ""
        if self.cursor_was_shown:
            output += hide_cursor_escape
            output += buildReturnToBottom(
                self.previous_line_count,
                self.previous_cursor_position,
            )
        if self.previous_line_count > 1:
            output += cursor_up(self.previous_line_count - 1)
        output += cursor_left()
        return output

    def __call__(self, text: str) -> bool:
        if self.previous_output == text:
            if self.cursor_position != self.previous_cursor_position and self.previous_output is not None:
                self.stream.write(
                    buildCursorOnlySequence(
                        cursor_was_shown=self.cursor_was_shown,
                        previous_line_count=self.previous_line_count,
                        previous_cursor_position=self.previous_cursor_position,
                        visible_line_count=max(self.previous_line_count - 1, 0),
                        cursor_position=self.cursor_position,
                    )
                )
                self.previous_cursor_position = self.cursor_position
                self.cursor_was_shown = self.cursor_position is not None
                return True
            return False

        output = ""
        visible_line_count = self._visible_line_count(text)
        if self.previous_output is None:
            if hasattr(self.stream, "isatty") and self.stream.isatty():
                output += hide_cursor_escape
            output += self._normalize(text)
        else:
            if self.incremental:
                output += self._return_to_top_prefix()
                output += self._incremental_payload(text)
            else:
                output += buildReturnToBottomPrefix(
                    self.cursor_was_shown,
                    self.previous_line_count,
                    self.previous_cursor_position,
                )
                output += erase_lines(self.previous_line_count)
                output += self._normalize(text)
        output += buildCursorSuffix(visible_line_count - 1 if visible_line_count else 0, self.cursor_position)
        self.stream.write(output)
        self.previous_output = text
        self.previous_line_count = visible_line_count
        self.previous_cursor_position = self.cursor_position
        self.cursor_was_shown = self.cursor_position is not None
        return True

    def _incremental_payload(self, text: str) -> str:
        previous_rows = self._visual_rows(self.previous_output or "")
        next_rows = self._visual_rows(text)
        max_rows = max(len(previous_rows), len(next_rows))

        first_diff = None
        last_diff = None
        for index in range(max_rows):
            previous_row = previous_rows[index] if index < len(previous_rows) else None
            next_row = next_rows[index] if index < len(next_rows) else None
            if previous_row != next_row:
                if first_diff is None:
                    first_diff = index
                last_diff = index

        if first_diff is None or last_diff is None:
            return ""

        payload = cursor_next_line() * first_diff
        current_row = first_diff

        for index in range(first_diff, last_diff + 1):
            previous_row = previous_rows[index] if index < len(previous_rows) else None
            next_row = next_rows[index] if index < len(next_rows) else None

            if index > current_row:
                payload += cursor_next_line() * (index - current_row)
                current_row = index

            if previous_row == next_row:
                continue

            payload += erase_line()
            if next_row is not None:
                payload += self._normalize(next_row)

        return payload

    def sync(self, text: str) -> None:
        visible_line_count = self._visible_line_count(text)
        if self.cursor_position is not None:
            if self.cursor_was_shown:
                self.stream.write(hide_cursor_escape)
            else:
                self.stream.write(buildCursorSuffix(visible_line_count - 1 if visible_line_count else 0, self.cursor_position))
        self.previous_output = text
        self.previous_line_count = visible_line_count
        self.previous_cursor_position = self.cursor_position
        self.cursor_was_shown = self.incremental and self.cursor_position is not None

    def clear(self) -> None:
        if self.previous_output is None:
            return
        output = buildReturnToBottomPrefix(
            self.cursor_was_shown,
            self.previous_line_count,
            self.previous_cursor_position,
        )
        output += erase_lines(self.previous_line_count)
        self.stream.write(output)
        self.previous_output = None
        self.previous_line_count = 0
        self.previous_cursor_position = None
        self.cursor_was_shown = False

    def reset(self) -> None:
        self.previous_output = None
        self.previous_line_count = 0
        self.previous_cursor_position = None
        self.cursor_was_shown = False

    def is_cursor_dirty(self) -> bool:
        return self.cursor_position != self.previous_cursor_position

    def will_render(self, text: str) -> bool:
        return self.previous_output != text or self.is_cursor_dirty()

    def done(self) -> None:
        if self.previous_output is not None and hasattr(self.stream, "isatty") and self.stream.isatty():
            self.stream.write(show_cursor_escape)
        self.previous_output = None
        self.previous_line_count = 0
        self.previous_cursor_position = None
        self.cursor_was_shown = False


def logUpdate(stream, incremental: bool = False) -> LogUpdate:
    return LogUpdate(stream, incremental=incremental)


__all__ = ["LogUpdate", "logUpdate"]
