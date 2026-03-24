from __future__ import annotations

from ..sanitize_ansi import sanitizeAnsi


class _StderrHandle:
    def __init__(self, stream, *, write=None) -> None:
        self.stream = stream
        self.stderr = stream
        self._overlay_writer = None
        self._write = write

    def bind_overlay_writer(self, writer) -> None:
        self._overlay_writer = writer

    def write(self, data: str) -> None:
        payload = sanitizeAnsi(data)
        if "The above error occurred in the <" in payload:
            return
        if self._write is not None:
            self._write(payload)
            return
        if self._overlay_writer is not None:
            self._overlay_writer(payload)
            return
        self.stream.write(payload)

    def raw_write(self, data: str) -> None:
        self.stream.write(data)


_stderr_handle = None


def _set_stderr_handle(handle) -> None:
    global _stderr_handle
    from ..components.StderrContext import StderrContext

    _stderr_handle = handle
    StderrContext.current_value = handle


def useStderr():
    from ..components.StderrContext import StderrContext

    return StderrContext.current_value


__all__ = ["useStderr", "_StderrHandle", "_set_stderr_handle"]
