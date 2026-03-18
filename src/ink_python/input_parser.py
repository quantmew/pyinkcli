"""
Streaming terminal input parser for ink-python.

This is a minimal parser that preserves escape sequences across reads and
separates bracketed paste payloads from regular input.
"""

from __future__ import annotations

from dataclasses import dataclass

_PENDING = object()

escape = "\x1b"
pasteStart = "\x1b[200~"
pasteEnd = "\x1b[201~"


@dataclass
class InputEvent:
    """Structured input event emitted by the parser."""

    kind: str
    data: str


class InputParser:
    """Incrementally parses stdin chunks into input and paste events."""

    _BRACKETED_PASTE_START = pasteStart
    _BRACKETED_PASTE_END = pasteEnd
    _FIXED_ESCAPE_SEQUENCES = {
        "\x1b[A",
        "\x1b[B",
        "\x1b[C",
        "\x1b[D",
        "\x1b[H",
        "\x1b[F",
        "\x1b[Z",
    }

    def __init__(self) -> None:
        self._buffer = ""

    def feed(self, chunk: str) -> list[InputEvent]:
        """Feed a chunk of input and return parsed events."""

        self._buffer += chunk
        events: list[InputEvent] = []

        while self._buffer:
            if self._buffer.startswith(self._BRACKETED_PASTE_START):
                end_index = self._buffer.find(
                    self._BRACKETED_PASTE_END,
                    len(self._BRACKETED_PASTE_START),
                )
                if end_index == -1:
                    break

                paste_start = len(self._BRACKETED_PASTE_START)
                paste_data = self._buffer[paste_start:end_index]
                events.append(InputEvent(kind="paste", data=paste_data))
                self._buffer = self._buffer[end_index + len(self._BRACKETED_PASTE_END):]
                continue

            if self._buffer[0] != "\x1b":
                events.append(InputEvent(kind="input", data=self._buffer[0]))
                self._buffer = self._buffer[1:]
                continue

            sequence = self._consume_escape_sequence()
            if sequence is None:
                break

            events.append(InputEvent(kind="input", data=sequence))

        return events

    def flush(self) -> list[InputEvent]:
        """Flush any remaining buffered input as literal input events."""

        if not self._buffer:
            return []

        events = [InputEvent(kind="input", data=char) for char in self._buffer]
        self._buffer = ""
        return events

    def _consume_escape_sequence(self) -> str | None:
        parsed = _parseEscapeSequence(self._buffer, 0)
        if parsed is _PENDING:
            return None
        if not parsed:
            return None

        sequence, next_index = parsed
        self._buffer = self._buffer[next_index:]
        return sequence


def isCsiParameterByte(byte: int) -> bool:
    return 0x30 <= byte <= 0x3F


def isCsiIntermediateByte(byte: int) -> bool:
    return 0x20 <= byte <= 0x2F


def isCsiFinalByte(byte: int) -> bool:
    return 0x40 <= byte <= 0x7E


def parseCsiSequence(sequence: str) -> str:
    parsed = _parseCsiSequence(sequence, 0, 1)
    if not parsed or parsed is _PENDING:
        return ""
    return parsed[0]


def parseSs3Sequence(sequence: str) -> str:
    parsed = _parseSs3Sequence(sequence, 0, 1)
    if not parsed or parsed is _PENDING:
        return ""
    return parsed[0]


def parseControlSequence(sequence: str) -> str:
    parsed = _parseControlSequence(sequence, 0, 1)
    if not parsed or parsed is _PENDING:
        return ""
    return parsed[0]


def parseEscapedCodePoint(sequence: str) -> str:
    parsed = _parseEscapedCodePoint(sequence, 0)
    if not parsed:
        return ""
    return parsed[0]


def parseEscapeSequence(sequence: str) -> str:
    parsed = _parseEscapeSequence(sequence, 0)
    if not parsed or parsed is _PENDING:
        return ""
    return parsed[0]


def _parseCsiSequence(
    sequence: str,
    start_index: int,
    prefix_length: int,
) -> tuple[str, int] | object | None:
    if not sequence.startswith("\x1b", start_index):
        return None

    csi_payload_start = start_index + prefix_length + 1
    index = csi_payload_start
    while index < len(sequence):
        byte = ord(sequence[index])
        if isCsiParameterByte(byte) or isCsiIntermediateByte(byte):
            index += 1
            continue

        if byte == 0x5B and index == csi_payload_start:
            index += 1
            continue

        if isCsiFinalByte(byte):
            return (sequence[start_index : index + 1], index + 1)

        return None

    return _PENDING


def _parseSs3Sequence(
    sequence: str,
    start_index: int,
    prefix_length: int,
) -> tuple[str, int] | object | None:
    next_index = start_index + prefix_length + 2
    if next_index > len(sequence):
        return _PENDING

    final_byte = ord(sequence[next_index - 1])
    if not isCsiFinalByte(final_byte):
        return None

    return (sequence[start_index:next_index], next_index)


def _parseControlSequence(
    sequence: str,
    start_index: int,
    prefix_length: int,
) -> tuple[str, int] | object | None:
    sequence_type_index = start_index + prefix_length
    if sequence_type_index >= len(sequence):
        return _PENDING

    sequence_type = sequence[sequence_type_index]
    if sequence_type == "[":
        return _parseCsiSequence(sequence, start_index, prefix_length)
    if sequence_type == "O":
        return _parseSs3Sequence(sequence, start_index, prefix_length)
    return None


def _parseEscapedCodePoint(
    sequence: str,
    escape_index: int,
) -> tuple[str, int] | None:
    if escape_index + 1 >= len(sequence):
        return None

    next_char = sequence[escape_index + 1]
    if next_char in {"[", "O"}:
        return None

    next_index = escape_index + 2
    return (sequence[escape_index:next_index], next_index)


def _parseEscapeSequence(
    sequence: str,
    escape_index: int,
) -> tuple[str, int] | object | None:
    if not sequence.startswith(escape, escape_index):
        return None

    if escape_index == len(sequence) - 1:
        return _PENDING

    next_char = sequence[escape_index + 1]
    if next_char == escape:
        if escape_index + 2 >= len(sequence):
            return _PENDING

        double_escape = _parseControlSequence(sequence, escape_index, 2)
        if double_escape is _PENDING:
            return _PENDING
        if double_escape:
            return double_escape
        return (sequence[escape_index : escape_index + 2], escape_index + 2)

    control = _parseControlSequence(sequence, escape_index, 1)
    if control is _PENDING:
        return _PENDING
    if control:
        return control

    return _parseEscapedCodePoint(sequence, escape_index)


def splitDeleteAndBackspace(sequence: str) -> list[str]:
    if sequence == "\x7f\x08":
        return ["\x7f", "\x08"]
    return [sequence]


def parseKeypresses(chunk: str) -> list[InputEvent]:
    parser = InputParser()
    events = parser.feed(chunk)
    return [item for event in events for item in (
        [InputEvent(kind=event.kind, data=piece) for piece in splitDeleteAndBackspace(event.data)]
        if event.kind == "input"
        else [event]
    )]


def createInputParser() -> InputParser:
    return InputParser()
