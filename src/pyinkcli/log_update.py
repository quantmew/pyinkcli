from __future__ import annotations

from .cursor_helpers import buildCursorOnlySequence, buildCursorSuffix, buildReturnToBottomPrefix
from .utils.ansi_escapes import cursor_next_line, cursor_up, erase_lines, hide_cursor_escape, show_cursor_escape


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
        if self.previous_output is None:
            if hasattr(self.stream, "isatty") and self.stream.isatty():
                output += hide_cursor_escape
            output += self._normalize(text)
        else:
            output += buildReturnToBottomPrefix(
                self.cursor_was_shown,
                self.previous_line_count,
                self.previous_cursor_position,
            )
            if self.incremental:
                output += self._incremental_payload(text)
            else:
                output += erase_lines(self.previous_line_count)
                output += self._normalize(text)
        output += buildCursorSuffix(text.count("\n"), self.cursor_position)
        self.stream.write(output)
        self.previous_output = text
        self.previous_line_count = text.count("\n") + 1
        self.previous_cursor_position = self.cursor_position
        self.cursor_was_shown = self.cursor_position is not None
        return True

    def _incremental_payload(self, text: str) -> str:
        if self.previous_output is None:
            return erase_lines(0) + self._normalize(text)
        previous_lines = self.previous_output.splitlines(True)
        next_lines = text.splitlines(True)
        common_prefix = 0
        while common_prefix < min(len(previous_lines), len(next_lines)):
            if previous_lines[common_prefix] != next_lines[common_prefix]:
                break
            common_prefix += 1
        if text == "\n":
            return erase_lines(self.previous_line_count) + "\n"
        if len(next_lines) < len(previous_lines):
            payload = erase_lines(max(self.previous_line_count - len(next_lines), 0))
            if next_lines:
                payload += cursor_up(1) + cursor_next_line()
            return payload
        changed_suffix = []
        for index in range(common_prefix, len(next_lines)):
            previous_line = previous_lines[index] if index < len(previous_lines) else None
            if previous_line == next_lines[index]:
                continue
            changed_suffix.append(next_lines[index])
        payload = cursor_next_line() * common_prefix
        payload += self._normalize("".join(changed_suffix))
        return payload

    def sync(self, text: str) -> None:
        if self.cursor_position is not None:
            if self.cursor_was_shown:
                self.stream.write(hide_cursor_escape)
            else:
                self.stream.write(buildCursorSuffix(text.count("\n"), self.cursor_position))
        self.previous_output = text
        self.previous_line_count = text.count("\n") + 1
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
