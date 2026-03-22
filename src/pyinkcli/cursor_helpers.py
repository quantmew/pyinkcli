from __future__ import annotations

from dataclasses import dataclass

from .utils.ansi_escapes import (
    cursor_down,
    cursor_left,
    cursor_to,
    cursor_up,
    hide_cursor_escape,
    show_cursor_escape,
)


@dataclass(frozen=True)
class CursorPosition:
    x: int
    y: int


@dataclass(frozen=True)
class CursorOnlyInput:
    cursorWasShown: bool
    previousLineCount: int
    previousCursorPosition: CursorPosition | None
    visibleLineCount: int
    cursorPosition: CursorPosition | None


def _coerce(position: tuple[int, int] | CursorPosition | None) -> CursorPosition | None:
    if position is None or isinstance(position, CursorPosition):
        return position
    return CursorPosition(*position)


def cursorPositionChanged(
    a: tuple[int, int] | CursorPosition | None,
    b: tuple[int, int] | CursorPosition | None,
) -> bool:
    left = _coerce(a)
    right = _coerce(b)
    return (left.x if left else None) != (right.x if right else None) or (
        left.y if left else None
    ) != (right.y if right else None)


def buildCursorSuffix(
    visibleLineCount: int,
    cursorPosition: tuple[int, int] | CursorPosition | None,
) -> str:
    position = _coerce(cursorPosition)
    if position is None:
        return ""
    move_up = visibleLineCount - position.y
    return (cursor_up(move_up) if move_up > 0 else "") + cursor_to(position.x) + show_cursor_escape


def buildReturnToBottom(
    previousLineCount: int,
    previousCursorPosition: tuple[int, int] | CursorPosition | None,
) -> str:
    position = _coerce(previousCursorPosition)
    if position is None:
        return ""
    down = previousLineCount - 1 - position.y
    return (cursor_down(down) if down > 0 else "") + cursor_left()


def buildReturnToBottomPrefix(
    cursorWasShown: bool,
    previousLineCount: int,
    previousCursorPosition: tuple[int, int] | CursorPosition | None,
) -> str:
    if not cursorWasShown:
        return ""
    return hide_cursor_escape + buildReturnToBottom(previousLineCount, previousCursorPosition)


def buildCursorOnlySequence(
    input: CursorOnlyInput | None = None,
    *,
    cursor_was_shown: bool | None = None,
    previous_line_count: int | None = None,
    previous_cursor_position: tuple[int, int] | CursorPosition | None = None,
    visible_line_count: int | None = None,
    cursor_position: tuple[int, int] | CursorPosition | None = None,
) -> str:
    if input is not None:
        return (
            (hide_cursor_escape if input.cursorWasShown else "")
            + buildReturnToBottom(input.previousLineCount, input.previousCursorPosition)
            + buildCursorSuffix(input.visibleLineCount, input.cursorPosition)
        )
    return (
        (hide_cursor_escape if cursor_was_shown else "")
        + buildReturnToBottom(previous_line_count or 0, previous_cursor_position)
        + buildCursorSuffix(visible_line_count or 0, cursor_position)
    )


showCursorEscape = show_cursor_escape
hideCursorEscape = hide_cursor_escape

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

