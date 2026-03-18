"""Utility modules for ink-python."""

import shutil
from typing import TextIO

from ink_python.utils.ansi_escapes import (
    cursor_to,
    cursor_move,
    cursor_up,
    cursor_down,
    cursor_forward,
    cursor_backward,
    cursor_left,
    cursor_save_position,
    cursor_restore_position,
    cursor_get_position,
    cursor_next_line,
    cursor_prev_line,
    cursor_hide,
    cursor_show,
    erase_lines,
    erase_end_line,
    erase_start_line,
    erase_line,
    erase_down,
    erase_up,
    erase_screen,
    scroll_up,
    scroll_down,
    clear_screen,
    clear_viewport,
    clear_terminal,
    enter_alternative_screen,
    exit_alternative_screen,
    begin_synchronized_output,
    end_synchronized_output,
    beep,
)
from ink_python.utils.string_width import string_width
from ink_python.utils.cli_boxes import BOXES, BoxStyle, get_box_style


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
