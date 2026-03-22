from __future__ import annotations

ESC = "\x1b["
OSC = "\x1b]"
BEL = "\x07"
SEP = ";"


def cursor_to(x: int, y: int | None = None) -> str:
    if y is None:
        return f"{ESC}{x + 1}G"
    return f"{ESC}{y + 1};{x + 1}H"


def cursor_move(x: int, y: int) -> str:
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
    return f"{ESC}{count}A"


def cursor_down(count: int = 1) -> str:
    return f"{ESC}{count}B"


def cursor_forward(count: int = 1) -> str:
    return f"{ESC}{count}C"


def cursor_backward(count: int = 1) -> str:
    return f"{ESC}{count}D"


def cursor_hide() -> str:
    return f"{ESC}?25l"


def cursor_show() -> str:
    return f"{ESC}?25h"


def erase_line() -> str:
    return f"{ESC}2K"


def erase_lines(count: int) -> str:
    clear = ""
    for index in range(count):
        clear += erase_line()
        if index < count - 1:
            clear += cursor_up()
    if count:
        clear += cursor_left()
    return clear


def erase_screen() -> str:
    return f"{ESC}2J"


def clear_terminal() -> str:
    return f"{ESC}2J{ESC}3J{ESC}H"


def enter_alternative_screen() -> str:
    return f"{ESC}?1049h"


def exit_alternative_screen() -> str:
    return f"{ESC}?1049l"


def beep() -> str:
    return BEL


def link(text: str, url: str) -> str:
    return f"{OSC}8;;{url}{BEL}{text}{OSC}8;;{BEL}"


def cursor_left() -> str:
    return f"{ESC}G"


def cursor_next_line() -> str:
    return f"{ESC}E"


cursorLeft = cursor_left
cursorNextLine = cursor_next_line
cursorTo = cursor_to
cursorMove = cursor_move
cursorUp = cursor_up
cursorDown = cursor_down
cursorForward = cursor_forward
cursorBackward = cursor_backward
cursorHide = cursor_hide
cursorShow = cursor_show
eraseLine = erase_line
eraseLines = erase_lines
eraseScreen = erase_screen
clearTerminal = clear_terminal
enterAlternativeScreen = enter_alternative_screen
exitAlternativeScreen = exit_alternative_screen
hide_cursor_escape = cursor_hide()
show_cursor_escape = cursor_show()

__all__ = [
    "beep",
    "clear_terminal",
    "clearTerminal",
    "cursor_backward",
    "cursor_down",
    "cursor_forward",
    "cursor_hide",
    "cursor_left",
    "cursor_move",
    "cursor_show",
    "cursor_to",
    "cursor_up",
    "cursorBackward",
    "cursorDown",
    "cursorForward",
    "cursorHide",
    "cursorLeft",
    "cursorNextLine",
    "cursor_next_line",
    "cursorMove",
    "cursorShow",
    "cursorTo",
    "cursorUp",
    "enter_alternative_screen",
    "enterAlternativeScreen",
    "erase_line",
    "erase_lines",
    "erase_screen",
    "eraseLine",
    "eraseLines",
    "eraseScreen",
    "exit_alternative_screen",
    "exitAlternativeScreen",
    "hide_cursor_escape",
    "link",
    "show_cursor_escape",
]
