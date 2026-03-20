"""
Cursor helper utilities for log_update.

Ported from js_source/ink/src/cursor-helpers.ts semantics.
"""

from __future__ import annotations

from typing import TypedDict

from pyinkcli.utils.ansi_escapes import (
    cursor_down,
    cursor_left,
    cursor_to,
    cursor_up,
    hide_cursor_escape,
    show_cursor_escape,
)

CursorPosition = tuple[int, int]
class CursorOnlyInput(TypedDict):
    cursorWasShown: bool
    previousLineCount: int
    previousCursorPosition: CursorPosition | None
    visibleLineCount: int
    cursorPosition: CursorPosition | None
showCursorEscape = show_cursor_escape
hideCursorEscape = hide_cursor_escape


def cursorPositionChanged(
    a: CursorPosition | None,
    b: CursorPosition | None,
) -> bool:
    return a != b


def buildCursorSuffix(
    visible_line_count: int,
    cursor_position: CursorPosition | None,
) -> str:
    if cursor_position is None:
        return ""

    x, y = cursor_position
    move_up = visible_line_count - y
    return (
        (cursor_up(move_up) if move_up > 0 else "")
        + cursor_to(x)
        + show_cursor_escape
    )


def buildReturnToBottom(
    previous_line_count: int,
    previous_cursor_position: CursorPosition | None,
) -> str:
    if previous_cursor_position is None:
        return ""

    _, y = previous_cursor_position
    down = previous_line_count - 1 - y
    return (cursor_down(down) if down > 0 else "") + cursor_left()


def buildCursorOnlySequence(
    *,
    cursor_was_shown: bool,
    previous_line_count: int,
    previous_cursor_position: CursorPosition | None,
    visible_line_count: int,
    cursor_position: CursorPosition | None,
) -> str:
    hide_prefix = hide_cursor_escape if cursor_was_shown else ""
    return (
        hide_prefix
        + buildReturnToBottom(previous_line_count, previous_cursor_position)
        + buildCursorSuffix(visible_line_count, cursor_position)
    )


def buildReturnToBottomPrefix(
    cursor_was_shown: bool,
    previous_line_count: int,
    previous_cursor_position: CursorPosition | None,
) -> str:
    if not cursor_was_shown:
        return ""

    return hide_cursor_escape + buildReturnToBottom(
        previous_line_count,
        previous_cursor_position,
    )


cursor_position_changed = cursorPositionChanged
build_cursor_suffix = buildCursorSuffix
build_return_to_bottom = buildReturnToBottom
build_cursor_only_sequence = buildCursorOnlySequence
build_return_to_bottom_prefix = buildReturnToBottomPrefix

__all__ = [
    "CursorPosition",
    "CursorOnlyInput",
    "showCursorEscape",
    "hideCursorEscape",
    "cursorPositionChanged",
    "buildCursorSuffix",
    "buildReturnToBottom",
    "buildCursorOnlySequence",
    "buildReturnToBottomPrefix",
]
