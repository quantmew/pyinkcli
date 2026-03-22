from __future__ import annotations

from dataclasses import dataclass

escape = "\x1b"
pasteStart = "\x1b[200~"
pasteEnd = "\x1b[201~"


@dataclass(frozen=True)
class InputEvent:
    kind: str
    data: str


def _is_csi_parameter_byte(byte: int) -> bool:
    return 0x30 <= byte <= 0x3F


def _is_csi_intermediate_byte(byte: int) -> bool:
    return 0x20 <= byte <= 0x2F


def _is_csi_final_byte(byte: int) -> bool:
    return 0x40 <= byte <= 0x7E


def parseCsiSequence(input: str, startIndex: int = 0, prefixLength: int = 1) -> str | None:
    csi_payload_start = startIndex + prefixLength + 1
    index = csi_payload_start
    while index < len(input):
        byte = ord(input[index])
        if _is_csi_parameter_byte(byte) or _is_csi_intermediate_byte(byte):
            index += 1
            continue
        if byte == 0x5B and index == csi_payload_start:
            index += 1
            continue
        if _is_csi_final_byte(byte):
            return input[startIndex:index + 1]
        return None
    return None


def parseSs3Sequence(input: str, startIndex: int = 0, prefixLength: int = 1) -> str | None:
    next_index = startIndex + prefixLength + 2
    if next_index > len(input):
        return None
    final_byte = ord(input[next_index - 1])
    if not _is_csi_final_byte(final_byte):
        return None
    return input[startIndex:next_index]


def parseEscapeSequence(input: str, escapeIndex: int = 0) -> str | None:
    if escapeIndex >= len(input) - 1:
        return None
    next_character = input[escapeIndex + 1]
    if next_character == escape:
        parsed = parseCsiSequence(input, escapeIndex, 2) or parseSs3Sequence(input, escapeIndex, 2)
        return parsed or input[escapeIndex:escapeIndex + 2]
    parsed = parseCsiSequence(input, escapeIndex, 1) or parseSs3Sequence(input, escapeIndex, 1)
    if parsed:
        return parsed
    next_codepoint = ord(input[escapeIndex + 1])
    next_codepoint_length = 2 if next_codepoint > 0xFFFF else 1
    return input[escapeIndex:escapeIndex + 1 + next_codepoint_length]


def _split_delete_and_backspace(text: str, events: list[InputEvent]) -> None:
    text_segment_start = 0
    for index, character in enumerate(text):
        if character in {"\x7f", "\x08"}:
            if index > text_segment_start:
                events.append(InputEvent("input", text[text_segment_start:index]))
            events.append(InputEvent("input", character))
            text_segment_start = index + 1
    if text_segment_start < len(text):
        events.append(InputEvent("input", text[text_segment_start:]))


def parseKeypresses(input: str) -> list[InputEvent]:
    parser = InputParser()
    return parser.feed(input)


class InputParser:
    def __init__(self) -> None:
        self._pending = ""

    def feed(self, chunk: str) -> list[InputEvent]:
        input = self._pending + chunk
        events: list[InputEvent] = []
        index = 0
        while index < len(input):
            escape_index = input.find(escape, index)
            if escape_index == -1:
                _split_delete_and_backspace(input[index:], events)
                self._pending = ""
                return events
            if escape_index > index:
                _split_delete_and_backspace(input[index:escape_index], events)
            parsed = parseEscapeSequence(input, escape_index)
            if parsed is None:
                self._pending = input[escape_index:]
                return events
            if parsed == pasteStart:
                after_start = escape_index + len(parsed)
                end_index = input.find(pasteEnd, after_start)
                if end_index == -1:
                    self._pending = input[escape_index:]
                    return events
                events.append(InputEvent("paste", input[after_start:end_index]))
                index = end_index + len(pasteEnd)
                continue
            events.append(InputEvent("input", parsed))
            index = escape_index + len(parsed)
        self._pending = ""
        return events

    def push(self, chunk: str) -> list[InputEvent]:
        return self.feed(chunk)

    def hasPendingEscape(self) -> bool:
        return bool(self._pending)

    def flushPendingEscape(self) -> str | None:
        if not self._pending:
            return None
        value = self._pending
        self._pending = ""
        return value

    def reset(self) -> None:
        self._pending = ""


def createInputParser() -> InputParser:
    return InputParser()


__all__ = [
    "InputEvent",
    "InputParser",
    "createInputParser",
    "parseCsiSequence",
    "parseEscapeSequence",
    "parseKeypresses",
    "parseSs3Sequence",
]

