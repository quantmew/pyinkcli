"""Patch global stdout/stderr writes to route through Ink output handlers."""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Literal, Protocol, TextIO

StreamName = Literal["stdout", "stderr"]


class _WriteHandler(Protocol):
    def __call__(self, stream: StreamName, data: str) -> None: ...


class _PatchedStream:
    def __init__(
        self,
        *,
        name: StreamName,
        original: TextIO,
        on_write: _WriteHandler,
    ) -> None:
        self._name = name
        self._original = original
        self._on_write = on_write
        self._buffer = ""

    def write(self, data: str) -> int:
        if not data:
            return 0

        self._buffer += data
        while True:
            newline_index = self._buffer.find("\n")
            if newline_index == -1:
                break

            chunk = self._buffer[: newline_index + 1]
            self._buffer = self._buffer[newline_index + 1 :]
            self._on_write(self._name, chunk)
        return len(data)

    def writelines(self, lines) -> None:
        for line in lines:
            self.write(line)

    def flush(self) -> None:
        if self._buffer:
            self._on_write(self._name, self._buffer)
            self._buffer = ""
        self._original.flush()

    def isatty(self) -> bool:
        return self._original.isatty() if hasattr(self._original, "isatty") else False

    @property
    def encoding(self):
        return getattr(self._original, "encoding", None)

    def __getattr__(self, name: str):
        return getattr(self._original, name)


def patch_console(on_write: _WriteHandler) -> Callable[[], None]:
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    sys.stdout = _PatchedStream(
        name="stdout",
        original=original_stdout,
        on_write=on_write,
    )
    sys.stderr = _PatchedStream(
        name="stderr",
        original=original_stderr,
        on_write=on_write,
    )

    def restore() -> None:
        sys.stdout.flush()
        sys.stderr.flush()
        sys.stdout = original_stdout
        sys.stderr = original_stderr

    return restore


__all__ = ["patch_console"]
