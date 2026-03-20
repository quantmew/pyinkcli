"""Tests for ANSI escapes utility."""

from pyinkcli.utils.ansi_escapes import (
    beep,
    clear_terminal,
    cursor_backward,
    cursor_down,
    cursor_forward,
    cursor_hide,
    cursor_left,
    cursor_move,
    cursor_show,
    cursor_to,
    cursor_up,
    enter_alternative_screen,
    erase_line,
    erase_lines,
    erase_screen,
    exit_alternative_screen,
    link,
)


def test_cursor_to():
    """Test cursor_to escape codes."""
    assert cursor_to(0) == "\x1B[1G"
    assert cursor_to(5) == "\x1B[6G"
    assert cursor_to(0, 0) == "\x1B[1;1H"
    assert cursor_to(10, 5) == "\x1B[6;11H"


def test_cursor_move():
    """Test cursor_move escape codes."""
    assert cursor_move(0, 0) == ""
    assert cursor_move(5, 0) == "\x1B[5C"
    assert cursor_move(-5, 0) == "\x1B[5D"
    assert cursor_move(0, 3) == "\x1B[3B"
    assert cursor_move(0, -3) == "\x1B[3A"


def test_cursor_up_down():
    """Test cursor up/down escape codes."""
    assert cursor_up() == "\x1B[1A"
    assert cursor_up(3) == "\x1B[3A"
    assert cursor_down() == "\x1B[1B"
    assert cursor_down(3) == "\x1B[3B"


def test_cursor_forward_backward():
    """Test cursor forward/backward escape codes."""
    assert cursor_forward() == "\x1B[1C"
    assert cursor_forward(5) == "\x1B[5C"
    assert cursor_backward() == "\x1B[1D"
    assert cursor_backward(5) == "\x1B[5D"


def test_cursor_left():
    """Test cursor_left escape code."""
    assert cursor_left() == "\x1B[G"


def test_cursor_hide_show():
    """Test cursor hide/show escape codes."""
    assert cursor_hide() == "\x1B[?25l"
    assert cursor_show() == "\x1B[?25h"


def test_erase_line():
    """Test erase_line escape code."""
    assert erase_line() == "\x1B[2K"


def test_erase_lines():
    """Test erase_lines escape code."""
    result = erase_lines(1)
    assert "\x1B[2K" in result
    assert "\x1B[G" in result


def test_erase_screen():
    """Test erase_screen escape code."""
    assert erase_screen() == "\x1B[2J"


def test_clear_terminal():
    """Test clear_terminal escape code."""
    result = clear_terminal()
    assert "\x1B[2J" in result
    assert "\x1B[H" in result


def test_alternative_screen():
    """Test alternative screen escape codes."""
    assert enter_alternative_screen() == "\x1B[?1049h"
    assert exit_alternative_screen() == "\x1B[?1049l"


def test_beep():
    """Test beep escape code."""
    assert beep() == "\x07"


def test_link():
    """Test link escape code."""
    result = link("Click here", "https://example.com")
    assert "Click here" in result
    assert "https://example.com" in result
