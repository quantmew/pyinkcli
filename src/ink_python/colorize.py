"""
Color utilities for ink-python.

Provides colorization using ANSI escape codes.
"""

from __future__ import annotations

from typing import Literal, Union

# ANSI color codes
COLORS: dict[str, int] = {
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
    "brightRed": 9,
    "brightGreen": 10,
    "brightYellow": 11,
    "brightBlue": 12,
    "brightMagenta": 13,
    "brightCyan": 14,
    "brightWhite": 15,
}

# Bright color aliases (using 90-97 range for dim compatibility)
BRIGHT_COLORS: dict[str, int] = {
    "bright-black": 90,
    "bright-red": 91,
    "bright-green": 92,
    "bright-yellow": 93,
    "bright-blue": 94,
    "bright-magenta": 95,
    "bright-cyan": 96,
    "bright-white": 97,
}


def colorize(
    text: str,
    color: str,
    type: Literal["foreground", "background"] = "foreground",
) -> str:
    """
    Apply color to text using ANSI escape codes.

    Args:
        text: The text to colorize.
        color: The color name or hex code.
        type: Whether to color foreground or background.

    Returns:
        The colorized text.
    """
    if not color:
        return text

    # Check for hex color
    if color.startswith("#"):
        return _colorize_hex(text, color, type)

    # Check for RGB color
    if color.startswith("rgb"):
        rgb = _parse_rgb(color)
        if rgb:
            return _colorize_rgb(text, rgb, type)

    # Check for 256 color
    if color.isdigit() or (color.startswith("color") and color[5:].isdigit()):
        num = int(color[5:] if color.startswith("color") else color)
        return _colorize_256(text, num, type)

    # Standard color name
    color_lower = color.lower()
    if color_lower in COLORS:
        code = COLORS[color_lower]
        if type == "foreground":
            return f"\x1b[{30 + code}m{text}\x1b[39m"
        else:
            return f"\x1b[{40 + code}m{text}\x1b[49m"

    # Bright color name
    if color_lower in BRIGHT_COLORS:
        code = BRIGHT_COLORS[color_lower]
        if type == "foreground":
            return f"\x1b[{code}m{text}\x1b[39m"
        else:
            return f"\x1b[{code + 10}m{text}\x1b[49m"

    # Unknown color - return unchanged
    return text


def _colorize_hex(text: str, hex_color: str, type: str) -> str:
    """Apply hex color to text."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c + c for c in hex_color)

    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except ValueError:
        return text

    return _colorize_rgb(text, (r, g, b), type)


def _colorize_rgb(text: str, rgb: tuple[int, int, int], type: str) -> str:
    """Apply RGB color to text."""
    r, g, b = rgb
    if type == "foreground":
        return f"\x1b[38;2;{r};{g};{b}m{text}\x1b[39m"
    else:
        return f"\x1b[48;2;{r};{g};{b}m{text}\x1b[49m"


def _colorize_256(text: str, color_num: int, type: str) -> str:
    """Apply 256-color to text."""
    if not 0 <= color_num <= 255:
        return text

    if type == "foreground":
        return f"\x1b[38;5;{color_num}m{text}\x1b[39m"
    else:
        return f"\x1b[48;5;{color_num}m{text}\x1b[49m"


def _parse_rgb(color: str) -> Optional[tuple[int, int, int]]:
    """Parse RGB color string."""
    import re

    match = re.match(r"rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", color)
    if match:
        r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if all(0 <= c <= 255 for c in (r, g, b)):
            return (r, g, b)
    return None


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c + c for c in hex_color)
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )
