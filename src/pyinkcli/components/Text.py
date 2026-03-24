from __future__ import annotations

from ..component import createElement

ANSI_OPEN = {
    "black": "\x1b[30m",
    "red": "\x1b[31m",
    "green": "\x1b[32m",
    "yellow": "\x1b[33m",
    "blue": "\x1b[34m",
    "magenta": "\x1b[35m",
    "cyan": "\x1b[36m",
    "white": "\x1b[37m",
    "gray": "\x1b[90m",
}
ANSI_BG_OPEN = {
    "red": "\x1b[41m",
    "green": "\x1b[42m",
    "yellow": "\x1b[43m",
    "blue": "\x1b[44m",
    "magenta": "\x1b[45m",
    "cyan": "\x1b[46m",
}


def _transform_text(text: str, props: dict) -> str:
    output = text
    prefixes: list[str] = []
    suffixes: list[str] = []
    if props.get("dimColor"):
        prefixes.append("\x1b[2m")
        suffixes.insert(0, "\x1b[22m")
    if props.get("bold"):
        prefixes.append("\x1b[1m")
        suffixes.insert(0, "\x1b[22m")
    if props.get("underline"):
        prefixes.append("\x1b[4m")
        suffixes.insert(0, "\x1b[24m")
    color = props.get("color")
    if color in ANSI_OPEN:
        prefixes.append(ANSI_OPEN[color])
        suffixes.append("\x1b[39m")
    background = props.get("backgroundColor")
    if background in ANSI_BG_OPEN:
        prefixes.append(ANSI_BG_OPEN[background])
        suffixes.append("\x1b[49m")
    return "".join(prefixes) + output + "".join(suffixes)


def Text(*children, **props):
    if not children:
        return None
    style = {
        "flexGrow": 0,
        "flexShrink": 1,
        "flexDirection": "row",
    }
    if "background_color" in props and "backgroundColor" not in props:
        props["backgroundColor"] = props["background_color"]
    style["textWrap"] = props.get("wrap", "wrap")
    props = dict(props)
    props["style"] = style
    props["internal_transform"] = lambda text: _transform_text(text, props)
    return createElement("ink-text", *children, **props)


__all__ = ["Text"]
