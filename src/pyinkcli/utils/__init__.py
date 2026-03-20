"""Utility modules for pyinkcli."""

import shutil
from typing import TextIO

from pyinkcli.utils.ansi_escapes import (
    beep,
    begin_synchronized_output,
    clear_screen,
    clear_terminal,
    clear_viewport,
    cursor_backward,
    cursor_down,
    cursor_forward,
    cursor_get_position,
    cursor_hide,
    cursor_left,
    cursor_move,
    cursor_next_line,
    cursor_prev_line,
    cursor_restore_position,
    cursor_save_position,
    cursor_show,
    cursor_to,
    cursor_up,
    end_synchronized_output,
    enter_alternative_screen,
    erase_down,
    erase_end_line,
    erase_line,
    erase_lines,
    erase_screen,
    erase_start_line,
    erase_up,
    exit_alternative_screen,
    scroll_down,
    scroll_up,
)
from pyinkcli.utils.cli_boxes import BOXES, BoxStyle, get_box_style
from pyinkcli.utils.string_width import string_width


def getWindowSize(stdout: TextIO) -> dict[str, int]:
    columns = getattr(stdout, "columns", None) or 0
    rows = getattr(stdout, "rows", None) or 0

    if columns and rows:
        return {"columns": columns, "rows": rows}

    try:
        fallback = shutil.get_terminal_size()
        return {
            "columns": columns or fallback.columns or 80,
            "rows": rows or fallback.lines or 24,
        }
    except Exception:
        return {"columns": columns or 80, "rows": rows or 24}

__all__ = [
    # ANSI escapes
    "cursor_to",
    "cursor_move",
    "cursor_up",
    "cursor_down",
    "cursor_forward",
    "cursor_backward",
    "cursor_left",
    "cursor_save_position",
    "cursor_restore_position",
    "cursor_get_position",
    "cursor_next_line",
    "cursor_prev_line",
    "cursor_hide",
    "cursor_show",
    "erase_lines",
    "erase_end_line",
    "erase_start_line",
    "erase_line",
    "erase_down",
    "erase_up",
    "erase_screen",
    "scroll_up",
    "scroll_down",
    "clear_screen",
    "clear_viewport",
    "clear_terminal",
    "enter_alternative_screen",
    "exit_alternative_screen",
    "begin_synchronized_output",
    "end_synchronized_output",
    "beep",
    "getWindowSize",
    # String width
    "string_width",
    # CLI boxes
    "BOXES",
    "BoxStyle",
    "get_box_style",
]
