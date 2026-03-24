"""Color utilities for pyinkcli.

Provides minimal Chalk-like colorization used by Text.
"""

from __future__ import annotations

import re


_COLORS = {
    "black": 0,
    "red": 1,
    "green": 2,
    "yellow": 3,
    "blue": 4,
    "magenta": 5,
    "cyan": 6,
    "white": 7,
    "gray": 8,
    "grey": 8,
}

_RGB_RE = re.compile(r"^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$")
_COLOR_TYPES = {"foreground", "background"}


def colorize(text: str, color: str | None, type: str) -> str:
    """Apply ANSI color to text."""
    if not color:
        return text
    if type not in _COLOR_TYPES:
        return text

    prefix = color_sequence(color, type)
    if prefix is None:
        return text
    return f"{prefix}{text}{_color_reset(type)}"


def color_sequence(color: str, type: str) -> str | None:
    if not color:
        return None
    if type not in _COLOR_TYPES:
        return None

    if color.startswith("#"):
        return _color_sequence_from_hex(color, type)
    if color.startswith("rgb"):
        return _color_sequence_from_rgb(color, type)
    if color.lower() in _COLORS:
        return _color_sequence_from_name(color, type)
    return None


def _color_sequence_from_hex(hex_color: str, type: str) -> str | None:
    value = hex_color.lstrip("#")
    if len(value) == 3:
        value = "".join(char * 2 for char in value)
    if len(value) != 6:
        return None

    try:
        r = int(value[0:2], 16)
        g = int(value[2:4], 16)
        b = int(value[4:6], 16)
    except ValueError:
        return None
    return _color_sequence_from_rgb_values((r, g, b), type)


def _color_sequence_from_rgb(color: str, type: str) -> str | None:
    match = _RGB_RE.match(color)
    if not match:
        return None

    r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
    if not all(0 <= value <= 255 for value in (r, g, b)):
        return None
    return _color_sequence_from_rgb_values((r, g, b), type)


def _color_sequence_from_rgb_values(rgb: tuple[int, int, int], type: str) -> str:
    r, g, b = rgb
    if type == "foreground":
        return f"\x1b[38;2;{r};{g};{b}m"
    return f"\x1b[48;2;{r};{g};{b}m"


def _color_sequence_from_name(color: str, type: str) -> str:
    code = _COLORS[color.lower()]
    if type == "foreground":
        return f"\x1b[{30 + code}m"
    return f"\x1b[{40 + code}m"


def _color_reset(type: str) -> str:
    return "\x1b[39m" if type == "foreground" else "\x1b[49m"


__all__ = ["colorize", "color_sequence"]
