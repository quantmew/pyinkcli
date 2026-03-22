from __future__ import annotations

from dataclasses import dataclass

bellCharacter = "\x07"
escapeCharacter = "\x1b"
stringTerminatorCharacter = "\x9c"
csiCharacter = "\x9b"
oscCharacter = "\x9d"
dcsCharacter = "\x90"
pmCharacter = "\x9e"
apcCharacter = "\x9f"
sosCharacter = "\x98"


@dataclass(frozen=True)
class AnsiToken:
    type: str
    value: str
    parameter_string: str = ""
    intermediate_string: str = ""
    final_character: str = ""


def _is_between(character: str, start: int, end: int) -> bool:
    code = ord(character)
    return start <= code <= end


def _is_csi_parameter_character(character: str) -> bool:
    return _is_between(character, 0x30, 0x3F)


def _is_csi_intermediate_character(character: str) -> bool:
    return _is_between(character, 0x20, 0x2F)


def _is_csi_final_character(character: str) -> bool:
    return _is_between(character, 0x40, 0x7E)


def _is_escape_intermediate_character(character: str) -> bool:
    return _is_between(character, 0x20, 0x2F)


def _is_escape_final_character(character: str) -> bool:
    return _is_between(character, 0x30, 0x7E)


def _is_c1_control_character(character: str) -> bool:
    return _is_between(character, 0x80, 0x9F)


def _read_csi_sequence(text: str, from_index: int) -> tuple[int, str, str, str] | None:
    index = from_index
    while index < len(text) and _is_csi_parameter_character(text[index]):
        index += 1
    parameter_string = text[from_index:index]
    intermediate_start_index = index
    while index < len(text) and _is_csi_intermediate_character(text[index]):
        index += 1
    intermediate_string = text[intermediate_start_index:index]
    if index >= len(text) or not _is_csi_final_character(text[index]):
        return None
    return index + 1, parameter_string, intermediate_string, text[index]


def _find_control_string_terminator_index(
    text: str, from_index: int, allow_bell_terminator: bool
) -> int | None:
    index = from_index
    while index < len(text):
        character = text[index]
        if allow_bell_terminator and character == bellCharacter:
            return index + 1
        if character == stringTerminatorCharacter:
            return index + 1
        if character == escapeCharacter:
            following_character = text[index + 1] if index + 1 < len(text) else None
            if following_character == escapeCharacter:
                index += 2
                continue
            if following_character == "\\":
                return index + 2
        index += 1
    return None


def _read_escape_sequence(text: str, from_index: int) -> tuple[int, str, str] | None:
    index = from_index
    while index < len(text) and _is_escape_intermediate_character(text[index]):
        index += 1
    intermediate_string = text[from_index:index]
    if index >= len(text) or not _is_escape_final_character(text[index]):
        return None
    return index + 1, intermediate_string, text[index]


def _control_string_from_escape(character: str) -> tuple[str, bool] | None:
    mapping = {
        "]": ("osc", True),
        "P": ("dcs", False),
        "^": ("pm", False),
        "_": ("apc", False),
        "X": ("sos", False),
    }
    return mapping.get(character)


def _control_string_from_c1(character: str) -> tuple[str, bool] | None:
    mapping = {
        oscCharacter: ("osc", True),
        dcsCharacter: ("dcs", False),
        pmCharacter: ("pm", False),
        apcCharacter: ("apc", False),
        sosCharacter: ("sos", False),
    }
    return mapping.get(character)


def _flush_text(tokens: list[AnsiToken], buffer: list[str]) -> None:
    if buffer:
        tokens.append(AnsiToken("text", "".join(buffer)))
        buffer.clear()


def hasAnsiControlCharacters(text: str) -> bool:
    return any(character == escapeCharacter or _is_c1_control_character(character) for character in text)


def tokenizeAnsi(text: str) -> list[AnsiToken]:
    tokens: list[AnsiToken] = []
    text_buffer: list[str] = []
    index = 0
    while index < len(text):
        character = text[index]
        if character == escapeCharacter:
            next_character = text[index + 1] if index + 1 < len(text) else None
            if next_character in ("[",):
                csi = _read_csi_sequence(text, index + 2)
                if csi is None:
                    _flush_text(tokens, text_buffer)
                    tokens.append(AnsiToken("invalid", text[index:]))
                    break
                end_index, parameter_string, intermediate_string, final_character = csi
                _flush_text(tokens, text_buffer)
                tokens.append(
                    AnsiToken(
                        "csi",
                        text[index:end_index],
                        parameter_string=parameter_string,
                        intermediate_string=intermediate_string,
                        final_character=final_character,
                    )
                )
                index = end_index
                continue
            control_string = _control_string_from_escape(next_character or "")
            if control_string is not None:
                token_type, allow_bell_terminator = control_string
                end_index = _find_control_string_terminator_index(text, index + 2, allow_bell_terminator)
                _flush_text(tokens, text_buffer)
                if end_index is None:
                    tokens.append(AnsiToken("invalid", text[index:]))
                    break
                tokens.append(AnsiToken(token_type, text[index:end_index]))
                index = end_index
                continue
            if next_character == "\\":
                _flush_text(tokens, text_buffer)
                tokens.append(AnsiToken("esc", text[index:index + 2], final_character="\\"))
                index += 2
                continue
            escape_sequence = _read_escape_sequence(text, index + 1)
            if escape_sequence is None:
                if next_character == "\x07":
                    index += 1
                    continue
                _flush_text(tokens, text_buffer)
                tokens.append(AnsiToken("invalid", text[index:]))
                break
            end_index, intermediate_string, final_character = escape_sequence
            _flush_text(tokens, text_buffer)
            tokens.append(
                AnsiToken(
                    "esc",
                    text[index:end_index],
                    intermediate_string=intermediate_string,
                    final_character=final_character,
                )
            )
            index = end_index
            continue
        if character == csiCharacter:
            csi = _read_csi_sequence(text, index + 1)
            _flush_text(tokens, text_buffer)
            if csi is None:
                tokens.append(AnsiToken("invalid", text[index:]))
                break
            end_index, parameter_string, intermediate_string, final_character = csi
            tokens.append(
                AnsiToken(
                    "csi",
                    text[index:end_index],
                    parameter_string=parameter_string,
                    intermediate_string=intermediate_string,
                    final_character=final_character,
                )
            )
            index = end_index
            continue
        c1_control = _control_string_from_c1(character)
        if c1_control is not None:
            token_type, allow_bell_terminator = c1_control
            end_index = _find_control_string_terminator_index(text, index + 1, allow_bell_terminator)
            _flush_text(tokens, text_buffer)
            if end_index is None:
                tokens.append(AnsiToken("invalid", text[index:]))
                break
            tokens.append(AnsiToken(token_type, text[index:end_index]))
            index = end_index
            continue
        if character == stringTerminatorCharacter:
            _flush_text(tokens, text_buffer)
            tokens.append(AnsiToken("st", character))
            index += 1
            continue
        if _is_c1_control_character(character):
            _flush_text(tokens, text_buffer)
            tokens.append(AnsiToken("c1", character))
            index += 1
            continue
        text_buffer.append(character)
        index += 1
    _flush_text(tokens, text_buffer)
    return tokens


__all__ = ["AnsiToken", "hasAnsiControlCharacters", "tokenizeAnsi"]

