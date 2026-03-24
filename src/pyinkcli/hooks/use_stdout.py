from __future__ import annotations

from ..sanitize_ansi import sanitizeAnsi


class _StdoutHandle:
    def __init__(self, stream, *, write=None) -> None:
        self.stream = stream
        self.stdout = stream
        self._overlay_writer = None
        self._write = write
        self.columns = getattr(stream, "columns", 80)
        self.rows = getattr(stream, "rows", 24)

    def bind_overlay_writer(self, writer) -> None:
        self._overlay_writer = writer

    def write(self, data: str) -> None:
        payload = sanitizeAnsi(data)
        if self._write is not None:
            self._write(payload)
            return
        if self._overlay_writer is not None:
            self._overlay_writer(payload)
            return
        self.stream.write(payload)

    def raw_write(self, data: str) -> None:
        self.stream.write(data)


_stdout_handle = None


def _set_stdout_handle(handle) -> None:
    global _stdout_handle
    from ..components.StdoutContext import StdoutContext

    _stdout_handle = handle
    StdoutContext.current_value = handle


def useStdout():
    from ..components.StdoutContext import StdoutContext

    return StdoutContext.current_value


__all__ = ["useStdout", "_StdoutHandle", "_set_stdout_handle"]
