"""
Wrap text with ANSI escape code support.

A Python port of the wrap-ansi JavaScript library.
"""

from __future__ import annotations

import re
from typing import Literal

from ink_python.utils.string_width import string_width

# ANSI escape sequence patterns
ANSI_ESCAPE = "\x1B"
ANSI_ESCAPE_CSI = "\x9B"
ANSI_CSI = "["
ANSI_OSC = "]"
ANSI_SGR_TERMINATOR = "m"
ANSI_ESCAPE_LINK = f"{ANSI_OSC}8;;"
ANSI_ESCAPE_BELL = "\x07"

ANSI_ESCAPE_REGEX = re.compile(
    rf"^\x1B(?:\[(?P<sgr>[0-9;]*){ANSI_SGR_TERMINATOR}|{ANSI_ESCAPE_LINK}(?P<uri>[^\x07\x1B]*)(?:\x07|\x1B\\))"
)
ANSI_ESCAPE_CSI_REGEX = re.compile(rf"^\x9B(?P<sgr>[0-9;]*){ANSI_SGR_TERMINATOR}")

TAB_SIZE = 8


def _get_graphemes(text: str) -> list[str]:
    """Split text into grapheme clusters."""
    # Simple implementation - just use character iteration
    # For full support, consider using the `grapheme` library
    return list(text)


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return ANSI_ESCAPE_REGEX.sub("", text)


def _word_lengths(text: str) -> list[int]:
    """Get the length of each word, ignoring ANSI codes."""
    return [string_width(word) for word in text.split(" ")]


def _wrap_word(rows: list[str], word: str, columns: int) -> None:
    """Wrap a long word across multiple rows."""
    characters = _get_graphemes(word)

    is_inside_escape = False
    is_inside_link_escape = False
    visible = string_width(_strip_ansi(rows[-1] if rows else ""))

    for index, character in enumerate(characters):
        char_length = string_width(character)

        if visible + char_length <= columns:
            if rows:
                rows[-1] += character
            else:
                rows.append(character)
        else:
            rows.append(character)
            visible = 0

        if character in (ANSI_ESCAPE, ANSI_ESCAPE_CSI):
            is_inside_escape = True
            if (
                character == ANSI_ESCAPE
                and index + 1 < len(characters)
                and characters[index + 1] != "\\"
            ):
                candidate = "".join(
                    characters[index + 1 : index + 1 + len(ANSI_ESCAPE_LINK)]
                )
                is_inside_link_escape = candidate == ANSI_ESCAPE_LINK

        if is_inside_escape:
            if is_inside_link_escape:
                if character in (ANSI_ESCAPE_BELL, "\\"):
                    is_inside_escape = False
                    is_inside_link_escape = False
            elif character == ANSI_SGR_TERMINATOR:
                is_inside_escape = False
            continue

        visible += char_length

        if visible == columns and index < len(characters) - 1:
            rows.append("")
            visible = 0

    # Handle edge case of last row being only ANSI escapes
    if not visible and rows and len(rows) > 1:
        rows[-2] += rows.pop()


def _string_visible_trim_spaces_right(text: str) -> str:
    """Trim spaces from right, ignoring invisible sequences."""
    words = text.split(" ")
    last = len(words)

    while last > 0:
        if string_width(words[last - 1]) > 0:
            break
        last -= 1

    if last == len(words):
        return text

    return " ".join(words[:last]) + "".join(words[last:])


def _expand_tabs(line: str) -> str:
    """Expand tabs to spaces."""
    if "\t" not in line:
        return line

    segments = line.split("\t")
    visible = 0
    expanded_line = ""

    for index, segment in enumerate(segments):
        expanded_line += segment
        visible += string_width(segment)

        if index < len(segments) - 1:
            spaces = TAB_SIZE - (visible % TAB_SIZE)
            expanded_line += " " * spaces
            visible += spaces

    return expanded_line


TextWrapMode = Literal["wrap", "end", "middle", "truncate-end", "truncate", "truncate-middle", "truncate-start"]


def wrap_ansi(
    text: str,
    columns: int,
    *,
    trim: bool = True,
    hard: bool = False,
    word_wrap: bool = True,
) -> str:
    """
    Wrap text to fit within specified column width, preserving ANSI escape codes.

    Args:
        text: The text to wrap.
        columns: The maximum number of columns per line.
        trim: Whether to trim whitespace from lines.
        hard: Whether to enforce hard wrapping (never exceed columns).
        word_wrap: Whether to wrap at word boundaries.

    Returns:
        The wrapped text.
    """
    if trim and text.strip() == "":
        return ""

    if columns <= 0:
        return text

    lengths = _word_lengths(text)
    rows = [""]

    for index, word in enumerate(text.split(" ")):
        if trim:
            rows[-1] = rows[-1].lstrip()

        row_length = string_width(rows[-1])

        if index != 0:
            if row_length >= columns and (not word_wrap or not trim):
                rows.append("")
                row_length = 0

            if row_length > 0 or not trim:
                rows[-1] += " "
                row_length += 1

        # Hard wrap mode
        if hard and word_wrap and lengths[index] > columns:
            remaining_columns = columns - row_length
            breaks_starting_this_line = 1 + (lengths[index] - remaining_columns - 1) // columns
            breaks_starting_next_line = (lengths[index] - 1) // columns
            if breaks_starting_next_line < breaks_starting_this_line:
                rows.append("")

            _wrap_word(rows, word, columns)
            continue

        if (
            row_length + lengths[index] > columns
            and row_length > 0
            and lengths[index] > 0
        ):
            if not word_wrap and row_length < columns:
                _wrap_word(rows, word, columns)
                continue
            rows.append("")

        if row_length + lengths[index] > columns and not word_wrap:
            _wrap_word(rows, word, columns)
            continue

        rows[-1] += word

    if trim:
        rows = [_string_visible_trim_spaces_right(row) for row in rows]

    return "\n".join(rows)


def wrap_text(
    text: str,
    width: int,
    wrap_mode: TextWrapMode = "wrap",
) -> str:
    """
    Wrap or truncate text based on the wrap mode.

    Args:
        text: The text to wrap/truncate.
        width: The maximum width.
        wrap_mode: How to handle text that exceeds the width.

    Returns:
        The wrapped or truncated text.
    """
    if wrap_mode == "wrap":
        return wrap_ansi(text, width)
    elif wrap_mode == "truncate" or wrap_mode == "truncate-end":
        return truncate_string(text, width, "end")
    elif wrap_mode == "truncate-start":
        return truncate_string(text, width, "start")
    elif wrap_mode == "truncate-middle":
        return truncate_string(text, width, "middle")
    else:
        return text


def truncate_string(
    text: str,
    width: int,
    position: Literal["start", "middle", "end"] = "end",
) -> str:
    """
    Truncate a string to fit within the specified width.

    Args:
        text: The text to truncate.
        width: The maximum width.
        position: Where to truncate (start, middle, or end).

    Returns:
        The truncated text.
    """
    text_width = string_width(text)

    if text_width <= width:
        return text

    if width <= 0:
        return ""

    # Strip ANSI for width calculation but preserve in output
    ellipsis = "…"
    ellipsis_width = string_width(ellipsis)
    available_width = width - ellipsis_width

    if available_width <= 0:
        return ellipsis[:width]

    if position == "end":
        # Truncate from end
        result = ""
        current_width = 0
        for char in text:
            char_width = string_width(char)
            if current_width + char_width > available_width:
                break
            result += char
            current_width += char_width
        return result + ellipsis

    elif position == "start":
        # Truncate from start
        result = ""
        current_width = 0
        for char in reversed(text):
            char_width = string_width(char)
            if current_width + char_width > available_width:
                break
            result = char + result
            current_width += char_width
        return ellipsis + result

    elif position == "middle":
        # Truncate from middle
        half_width = available_width // 2
        left = ""
        right = ""
        left_width = 0
        right_width = 0

        # Build left part
        for char in text:
            char_width = string_width(char)
            if left_width + char_width > half_width:
                break
            left += char
            left_width += char_width

        # Build right part
        for char in reversed(text):
            char_width = string_width(char)
            if right_width + char_width > available_width - half_width:
                break
            right = char + right
            right_width += char_width

        return left + ellipsis + right

    return text
