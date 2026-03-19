"""
ANSI tokenizer utilities.

Python counterpart to js_source/ink/src/ansi-tokenizer.ts.
"""

from __future__ import annotations

from dataclasses import dataclass

bellCharacter = "\u0007"
escapeCharacter = "\u001B"
stringTerminatorCharacter = "\u009C"
csiCharacter = "\u009B"
oscCharacter = "\u009D"
dcsCharacter = "\u0090"
pmCharacter = "\u009E"
apcCharacter = "\u009F"
sosCharacter = "\u0098"


@dataclass(frozen=True)
class AnsiToken:
    type: str
    value: str
    parameter_string: str = ""
    intermediate_string: str = ""
    final_character: str = ""


def hasAnsiControlCharacters(text: str) -> bool:
    if escapeCharacter in text:
        return True

    return any(_is_c1_control_character(character) for character in text)


def tokenizeAnsi(text: str) -> list[AnsiToken]:
    if not hasAnsiControlCharacters(text):
        return [AnsiToken(type="text", value=text)]

    tokens: list[AnsiToken] = []
    text_start_index = 0
    index = 0

    while index < len(text):
        character = text[index]

        if character == escapeCharacter:
            following_character = text[index + 1] if index + 1 < len(text) else None
            if following_character is None:
                return _malformed_from_index(tokens, text, text_start_index, index)

            if following_character == "[":
                csi_sequence = _read_csi_sequence(text, index + 2)
                if csi_sequence is None:
                    return _malformed_from_index(tokens, text, text_start_index, index)

                if index > text_start_index:
                    tokens.append(AnsiToken(type="text", value=text[text_start_index:index]))

                end_index, parameter_string, intermediate_string, final_character = csi_sequence
                tokens.append(
                    AnsiToken(
                        type="csi",
                        value=text[index:end_index],
                        parameter_string=parameter_string,
                        intermediate_string=intermediate_string,
                        final_character=final_character,
                    )
                )
                index = end_index
                text_start_index = index
                continue

            escape_control_string = _get_control_string_from_escape_introducer(
                following_character
            )
            if escape_control_string is not None:
                control_string_terminator_index = _find_control_string_terminator_index(
                    text,
                    index + 2,
                    escape_control_string["allow_bell_terminator"],
                )
                if control_string_terminator_index is None:
                    return _malformed_from_index(tokens, text, text_start_index, index)

                if index > text_start_index:
                    tokens.append(AnsiToken(type="text", value=text[text_start_index:index]))

                tokens.append(
                    AnsiToken(
                        type=escape_control_string["type"],
                        value=text[index:control_string_terminator_index],
                    )
                )
                index = control_string_terminator_index
                text_start_index = index
                continue

            escape_sequence = _read_escape_sequence(text, index + 1)
            if escape_sequence is None:
                if _is_escape_intermediate_character(following_character):
                    return _malformed_from_index(tokens, text, text_start_index, index)

                if index > text_start_index:
                    tokens.append(AnsiToken(type="text", value=text[text_start_index:index]))

                index += 1
                text_start_index = index
                continue

            if index > text_start_index:
                tokens.append(AnsiToken(type="text", value=text[text_start_index:index]))

            end_index, intermediate_string, final_character = escape_sequence
            tokens.append(
                AnsiToken(
                    type="esc",
                    value=text[index:end_index],
                    intermediate_string=intermediate_string,
                    final_character=final_character,
                )
            )
            index = end_index
            text_start_index = index
            continue

        if character == csiCharacter:
            csi_sequence = _read_csi_sequence(text, index + 1)
            if csi_sequence is None:
                return _malformed_from_index(tokens, text, text_start_index, index)

            if index > text_start_index:
                tokens.append(AnsiToken(type="text", value=text[text_start_index:index]))

            end_index, parameter_string, intermediate_string, final_character = csi_sequence
            tokens.append(
                AnsiToken(
                    type="csi",
                    value=text[index:end_index],
                    parameter_string=parameter_string,
                    intermediate_string=intermediate_string,
                    final_character=final_character,
                )
            )
            index = end_index
            text_start_index = index
            continue

        c1_control_string = _get_control_string_from_c1_introducer(character)
        if c1_control_string is not None:
            control_string_terminator_index = _find_control_string_terminator_index(
                text,
                index + 1,
                c1_control_string["allow_bell_terminator"],
            )
            if control_string_terminator_index is None:
                return _malformed_from_index(tokens, text, text_start_index, index)

            if index > text_start_index:
                tokens.append(AnsiToken(type="text", value=text[text_start_index:index]))

            tokens.append(
                AnsiToken(
                    type=c1_control_string["type"],
                    value=text[index:control_string_terminator_index],
                )
            )
            index = control_string_terminator_index
            text_start_index = index
            continue

        if character == stringTerminatorCharacter:
            if index > text_start_index:
                tokens.append(AnsiToken(type="text", value=text[text_start_index:index]))
            tokens.append(AnsiToken(type="st", value=character))
            index += 1
            text_start_index = index
            continue

        if _is_c1_control_character(character):
            if index > text_start_index:
                tokens.append(AnsiToken(type="text", value=text[text_start_index:index]))
            tokens.append(AnsiToken(type="c1", value=character))
            index += 1
            text_start_index = index
            continue

        index += 1

    if text_start_index < len(text):
        tokens.append(AnsiToken(type="text", value=text[text_start_index:]))

    return tokens


def _read_csi_sequence(text: str, from_index: int) -> tuple[int, str, str, str] | None:
    index = from_index
    while index < len(text) and _is_csi_parameter_character(text[index]):
        index += 1
    parameter_string = text[from_index:index]

    intermediate_start_index = index
    while index < len(text) and _is_csi_intermediate_character(text[index]):
        index += 1
    intermediate_string = text[intermediate_start_index:index]

    final_character = text[index] if index < len(text) else None
    if final_character is None or not _is_csi_final_character(final_character):
        return None

    return (index + 1, parameter_string, intermediate_string, final_character)


def _find_control_string_terminator_index(
    text: str,
    from_index: int,
    allow_bell_terminator: bool,
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

    final_character = text[index] if index < len(text) else None
    if final_character is None or not _is_escape_final_character(final_character):
        return None

    return (index + 1, text[from_index:index], final_character)


def _get_control_string_from_escape_introducer(character: str) -> dict[str, object] | None:
    if character == "]":
        return {"type": "osc", "allow_bell_terminator": True}
    if character == "P":
        return {"type": "dcs", "allow_bell_terminator": False}
    if character == "^":
        return {"type": "pm", "allow_bell_terminator": False}
    if character == "_":
        return {"type": "apc", "allow_bell_terminator": False}
    if character == "X":
        return {"type": "sos", "allow_bell_terminator": False}
    return None


def _get_control_string_from_c1_introducer(character: str) -> dict[str, object] | None:
    if character == oscCharacter:
        return {"type": "osc", "allow_bell_terminator": True}
    if character == dcsCharacter:
        return {"type": "dcs", "allow_bell_terminator": False}
    if character == pmCharacter:
        return {"type": "pm", "allow_bell_terminator": False}
    if character == apcCharacter:
        return {"type": "apc", "allow_bell_terminator": False}
    if character == sosCharacter:
        return {"type": "sos", "allow_bell_terminator": False}
    return None


def _malformed_from_index(
    tokens: list[AnsiToken],
    text: str,
    text_start_index: int,
    from_index: int,
) -> list[AnsiToken]:
    if from_index > text_start_index:
        tokens.append(AnsiToken(type="text", value=text[text_start_index:from_index]))
    tokens.append(AnsiToken(type="invalid", value=text[from_index:]))
    return tokens


def _is_csi_parameter_character(character: str) -> bool:
    code_point = ord(character)
    return 0x30 <= code_point <= 0x3F


def _is_csi_intermediate_character(character: str) -> bool:
    code_point = ord(character)
    return 0x20 <= code_point <= 0x2F


def _is_csi_final_character(character: str) -> bool:
    code_point = ord(character)
    return 0x40 <= code_point <= 0x7E


def _is_escape_intermediate_character(character: str) -> bool:
    code_point = ord(character)
    return 0x20 <= code_point <= 0x2F


def _is_escape_final_character(character: str) -> bool:
    code_point = ord(character)
    return 0x30 <= code_point <= 0x7E


def _is_c1_control_character(character: str) -> bool:
    code_point = ord(character)
    return 0x80 <= code_point <= 0x9F
