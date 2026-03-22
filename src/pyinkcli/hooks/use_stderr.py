from __future__ import annotations

from ..sanitize_ansi import sanitizeAnsi


class _StderrHandle:
    def __init__(self, stream) -> None:
        self.stream = stream
        self._overlay_writer = None

    def bind_overlay_writer(self, writer) -> None:
        self._overlay_writer = writer

    def write(self, data: str) -> None:
        payload = sanitizeAnsi(data)
        if "The above error occurred in the <" in payload:
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
    _stderr_handle = handle


def useStderr():
    return _stderr_handle


__all__ = ["useStderr", "_StderrHandle", "_set_stderr_handle"]

