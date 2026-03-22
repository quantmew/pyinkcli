from __future__ import annotations

from ..sanitize_ansi import sanitizeAnsi


class _StdoutHandle:
    def __init__(self, stream) -> None:
        self.stream = stream
        self._overlay_writer = None
        self.columns = getattr(stream, "columns", 80)
        self.rows = getattr(stream, "rows", 24)

    def bind_overlay_writer(self, writer) -> None:
        self._overlay_writer = writer

    def write(self, data: str) -> None:
        payload = sanitizeAnsi(data)
        if self._overlay_writer is not None:
            self._overlay_writer(payload)
            return
        self.stream.write(payload)

    def raw_write(self, data: str) -> None:
        self.stream.write(data)


_stdout_handle = None


def _set_stdout_handle(handle) -> None:
    global _stdout_handle
    _stdout_handle = handle


def useStdout():
    return _stdout_handle


__all__ = ["useStdout", "_StdoutHandle", "_set_stdout_handle"]
