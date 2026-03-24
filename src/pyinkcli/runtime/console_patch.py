from __future__ import annotations

import sys
from typing import TextIO


class PatchedConsoleStream:
    def __init__(self, writer, original_stream) -> None:
        self._writer = writer
        self._original_stream = original_stream
        self._buffer = ""

    def write(self, data: str) -> int:
        self._buffer += data
        if "\n" in self._buffer:
            last_newline = self._buffer.rfind("\n")
            payload = self._buffer[: last_newline + 1]
            self._buffer = self._buffer[last_newline + 1 :]
            self._writer(payload)
        return len(data)

    def flush(self) -> None:
        if self._buffer:
            self._writer(self._buffer)
            self._buffer = ""
        flush = getattr(self._original_stream, "flush", None)
        if callable(flush):
            flush()

    def isatty(self) -> bool:
        return bool(getattr(self._original_stream, "isatty", lambda: False)())

    @property
    def encoding(self):
        return getattr(self._original_stream, "encoding", "utf-8")


class ConsolePatch:
    def __init__(self, stdout_writer, stderr_writer, stdout_stream, stderr_stream) -> None:
        self._stdout_writer = stdout_writer
        self._stderr_writer = stderr_writer
        self._stdout_stream = stdout_stream
        self._stderr_stream = stderr_stream
        self._restore_stdout: TextIO | None = None
        self._restore_stderr: TextIO | None = None

    def patch(self) -> None:
        if self._restore_stdout is not None or self._restore_stderr is not None:
            return
        self._restore_stdout = sys.stdout
        self._restore_stderr = sys.stderr
        sys.stdout = PatchedConsoleStream(self._stdout_writer, self._stdout_stream)
        sys.stderr = PatchedConsoleStream(self._stderr_writer, self._stderr_stream)

    def restore(self) -> None:
        if self._restore_stdout is not None:
            sys.stdout = self._restore_stdout
            self._restore_stdout = None
        if self._restore_stderr is not None:
            sys.stderr = self._restore_stderr
            self._restore_stderr = None


__all__ = ["ConsolePatch", "PatchedConsoleStream"]
