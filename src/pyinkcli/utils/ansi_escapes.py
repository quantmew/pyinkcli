"""
ANSI escape codes for terminal control.

A Python port of the ansi-escapes JavaScript library.
"""

from __future__ import annotations

import os
import sys

ESC = "\u001B["
OSC = "\u001B]"
BEL = "\u0007"
SEP = ";"

_is_windows = sys.platform == "win32"


def _is_tmux() -> bool:
    """Check if running inside tmux."""
    term = os.environ.get("TERM", "")
    return (
        term.startswith("screen")
        or term.startswith("tmux")
        or os.environ.get("TMUX") is not None
    )


def _wrap_osc(sequence: str) -> str:
    """Wrap OSC sequence for tmux compatibility."""
    if _is_tmux():
        # Tmux requires OSC sequences to be wrapped with DCS tmux; <sequence> ST
        return "\u001BPtmux;" + sequence.replace("\u001B", "\u001B\u001B") + "\u001B\\"
    return sequence


def cursor_to(x: int, y: int | None = None) -> str:
    """Move cursor to position."""
    if y is None:
        return f"{ESC}{x + 1}G"
    return f"{ESC}{y + 1}{SEP}{x + 1}H"


def cursor_move(x: int, y: int) -> str:
    """Move cursor by offset."""
    result = ""
    if x < 0:
        result += f"{ESC}{-x}D"
    elif x > 0:
        result += f"{ESC}{x}C"
    if y < 0:
        result += f"{ESC}{-y}A"
    elif y > 0:
        result += f"{ESC}{y}B"
    return result


def cursor_up(count: int = 1) -> str:
    """Move cursor up."""
    return f"{ESC}{count}A"


def cursor_down(count: int = 1) -> str:
    """Move cursor down."""
    return f"{ESC}{count}B"


def cursor_forward(count: int = 1) -> str:
    """Move cursor forward."""
    return f"{ESC}{count}C"


def cursor_backward(count: int = 1) -> str:
    """Move cursor backward."""
    return f"{ESC}{count}D"


def cursor_left() -> str:
    """Move cursor to beginning of line."""
    return f"{ESC}G"


def cursor_save_position() -> str:
    """Save cursor position."""
    return "\u001B7"


def cursor_restore_position() -> str:
    """Restore cursor position."""
    return "\u001B8"


def cursor_get_position() -> str:
    """Get cursor position (request)."""
    return f"{ESC}6n"


def cursor_next_line() -> str:
    """Move cursor to next line."""
    return f"{ESC}E"


def cursor_prev_line() -> str:
    """Move cursor to previous line."""
    return f"{ESC}F"


def cursor_hide() -> str:
    """Hide cursor."""
    return f"{ESC}?25l"


def cursor_show() -> str:
    """Show cursor."""
    return f"{ESC}?25h"


def erase_lines(count: int) -> str:
    """Erase specified number of lines."""
    clear = ""
    for i in range(count):
        clear += erase_line()
        if i < count - 1:
            clear += cursor_up()
    if count:
        clear += cursor_left()
    return clear


def erase_end_line() -> str:
    """Erase from cursor to end of line."""
    return f"{ESC}K"


def erase_start_line() -> str:
    """Erase from start of line to cursor."""
    return f"{ESC}1K"


def erase_line() -> str:
    """Erase entire line."""
    return f"{ESC}2K"


def erase_down() -> str:
    """Erase from cursor to end of screen."""
    return f"{ESC}J"


def erase_up() -> str:
    """Erase from start of screen to cursor."""
    return f"{ESC}1J"


def erase_screen() -> str:
    """Erase entire screen."""
    return f"{ESC}2J"


def scroll_up() -> str:
    """Scroll screen up."""
    return f"{ESC}S"


def scroll_down() -> str:
    """Scroll screen down."""
    return f"{ESC}T"


def clear_screen() -> str:
    """Clear screen and reset."""
    return "\u001Bc"


def clear_viewport() -> str:
    """Clear viewport and move cursor to home."""
    return f"{erase_screen()}{ESC}H"


def clear_terminal() -> str:
    """Clear terminal including scrollback."""
    return f"{erase_screen()}{ESC}3J{ESC}H"


def enter_alternative_screen() -> str:
    """Enter alternative screen buffer."""
    return f"{ESC}?1049h"


def exit_alternative_screen() -> str:
    """Exit alternative screen buffer."""
    return f"{ESC}?1049l"


def begin_synchronized_output() -> str:
    """Begin synchronized output."""
    return f"{ESC}?2026h"


def end_synchronized_output() -> str:
    """End synchronized output."""
    return f"{ESC}?2026l"


def synchronized_output(text: str) -> str:
    """Wrap text in synchronized output."""
    return begin_synchronized_output() + text + end_synchronized_output()


def beep() -> str:
    """Terminal beep."""
    return BEL


def link(text: str, url: str) -> str:
    """Create a clickable link."""
    open_link = _wrap_osc(f"{OSC}8{SEP}{SEP}{url}{BEL}")
    close_link = _wrap_osc(f"{OSC}8{SEP}{SEP}{BEL}")
    return open_link + text + close_link


# Convenient aliases
hide_cursor_escape = cursor_hide()
show_cursor_escape = cursor_show()
bsu = begin_synchronized_output()
esu = end_synchronized_output()
