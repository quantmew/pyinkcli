from __future__ import annotations

from io import BytesIO, StringIO

from ink_python.ink import Ink, Options


class _StdinWithBuffer:
    def __init__(self, data: bytes) -> None:
        self.buffer = BytesIO(data)

    def isatty(self) -> bool:
        return True


def _make_ink_with_stdin(data: bytes) -> Ink:
    stdout = StringIO()
    stdin = _StdinWithBuffer(data)
    stderr = StringIO()
    return Ink(
        Options(
            stdout=stdout,
            stdin=stdin,
            stderr=stderr,
            interactive=False,
            patch_console=False,
        )
    )


def test_read_stdin_chunk_decodes_utf8_multibyte_sequences() -> None:
    ink = _make_ink_with_stdin("中文".encode("utf-8"))
    try:
        assert ink._read_stdin_chunk() == "中"
        assert ink._read_stdin_chunk() == "文"
    finally:
        ink.unmount()


def test_read_stdin_chunk_replaces_invalid_utf8_like_node_string_decoder() -> None:
    ink = _make_ink_with_stdin(b"\xff")
    try:
        assert ink._read_stdin_chunk() == "\ufffd"
    finally:
        ink.unmount()
