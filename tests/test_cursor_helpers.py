"""Tests for cursor helper escape sequence builders."""

from pyinkcli.cursor_helpers import (
    buildCursorOnlySequence,
    buildCursorSuffix,
    buildReturnToBottom,
    buildReturnToBottomPrefix,
    cursorPositionChanged,
)
from pyinkcli.utils.ansi_escapes import cursor_down, cursor_left, cursor_to, cursor_up, hide_cursor_escape, show_cursor_escape


def test_cursor_position_changed():
    assert cursorPositionChanged((1, 2), (1, 3)) is True
    assert cursorPositionChanged((1, 2), (1, 2)) is False
    assert cursorPositionChanged(None, (1, 2)) is True


def test_build_cursor_suffix():
    suffix = buildCursorSuffix(3, (5, 1))
    assert suffix == cursor_up(2) + cursor_to(5) + show_cursor_escape


def test_build_return_to_bottom():
    result = buildReturnToBottom(4, (5, 1))
    assert result == cursor_down(2) + cursor_left()


def test_build_return_to_bottom_prefix():
    result = buildReturnToBottomPrefix(True, 4, (5, 1))
    assert result == hide_cursor_escape + cursor_down(2) + cursor_left()


def test_build_cursor_only_sequence():
    result = buildCursorOnlySequence(
        cursor_was_shown=True,
        previous_line_count=4,
        previous_cursor_position=(5, 1),
        visible_line_count=3,
        cursor_position=(2, 0),
    )
    assert result == (
        hide_cursor_escape
        + cursor_down(2)
        + cursor_left()
        + cursor_up(3)
        + cursor_to(2)
        + show_cursor_escape
    )
