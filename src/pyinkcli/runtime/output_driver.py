from __future__ import annotations

import os

from ..sanitize_ansi import sanitizeAnsi
from ..log_update import logUpdate
from ..utils.ansi_escapes import clear_terminal, hide_cursor_escape
from ..write_synchronized import bsu, esu, shouldSynchronize


class OutputDriver:
    def __init__(self, stream, *, interactive: bool = False, debug: bool = False, incremental: bool = False) -> None:
        self.stream = stream
        self.interactive = interactive
        self.debug = debug
        self.incremental = incremental
        self.log = logUpdate(stream, incremental=incremental)
        self.last_output = ""
        self.last_output_to_render = ""
        self.last_output_height = 0
        self.full_static_output = ""

    def _can_rewrite_stream(self) -> bool:
        if not hasattr(self.stream, "seek") or not hasattr(self.stream, "truncate"):
            return False
        seekable = getattr(self.stream, "seekable", None)
        if callable(seekable):
            try:
                return bool(seekable())
            except Exception:  # noqa: BLE001
                return False
        return True

    def set_cursor_position(self, position) -> None:
        self.log.set_cursor_position(position)

    def render_frame(self, output: str, *, static_output: str = "", force_clear: bool = False) -> bool:
        output_height = 0 if output == "" else output.count("\n") + 1
        has_static_output = bool(static_output and static_output != "\n")
        sync = shouldSynchronize(self.stream, self.interactive)
        was_fullscreen = self._is_fullscreen(self.last_output_height)
        is_fullscreen = self._is_fullscreen(output_height)

        if self.debug:
            if has_static_output:
                self.full_static_output += static_output
            if self._can_rewrite_stream():
                self.stream.seek(0)
                self.stream.truncate(0)
            if sync:
                self.stream.write(bsu)
            self.stream.write(sanitizeAnsi(self.full_static_output + output))
            if sync:
                self.stream.write(esu)
            self.last_output = output
            self.last_output_to_render = output
            self.last_output_height = output_height
            return True

        if not self.interactive:
            if self._can_rewrite_stream():
                self.stream.seek(0)
                self.stream.truncate(0)
            if has_static_output:
                self.stream.write(static_output)
            self.stream.write(output)
            self.last_output = output
            self.last_output_to_render = output
            self.last_output_height = output_height
            return True

        if has_static_output:
            self.full_static_output += static_output

        output_to_render = output if is_fullscreen else output + "\n"
        prepend_clear = False
        if force_clear or (was_fullscreen and not is_fullscreen):
            prepend_clear = True
            self.log.reset()
        if has_static_output:
            if sync:
                self.stream.write(bsu)
            if prepend_clear:
                self.stream.write(clear_terminal())
            self.log.clear()
            static_payload = static_output if static_output.endswith("\n") else static_output + "\n"
            self.stream.write(self.log._normalize(static_payload))
            if self.log.previous_output is None:
                self.stream.write(self.log._normalize(output_to_render))
                self.log.sync(output_to_render)
            else:
                self.log(output_to_render)
            if sync:
                self.stream.write(esu)
        elif output != self.last_output or self.log.is_cursor_dirty():
            if sync:
                self.stream.write(bsu)
            if prepend_clear:
                self.stream.write(clear_terminal())
            self.log(output_to_render)
            if sync:
                self.stream.write(esu)
        else:
            return False
        self.last_output = output
        self.last_output_to_render = output_to_render
        self.last_output_height = output_height
        return True

    def overlay_stdout(self, text: str) -> None:
        if self.debug:
            self.stream.write(text + self.last_output)
            return
        if self.interactive:
            sync = shouldSynchronize(self.stream, self.interactive)
            if sync:
                self.stream.write(bsu)
            self.log.clear()
            self.stream.write(text)
            if self.last_output_to_render:
                self.log(self.last_output_to_render)
            if sync:
                self.stream.write(esu)
            return
        self.stream.write(text + self.last_output)

    def overlay_stderr(self, text: str) -> None:
        self.stream.write(text)

    def finish(self) -> None:
        self.log.done()

    def _is_fullscreen(self, output_height: int) -> bool:
        if not hasattr(self.stream, "isatty") or not self.stream.isatty():
            return False
        rows = getattr(self.stream, "rows", None)
        if rows is None and hasattr(self.stream, "fileno"):
            try:
                rows = os.get_terminal_size(self.stream.fileno()).lines
            except OSError:
                rows = 24
        return output_height >= (rows or 24)
