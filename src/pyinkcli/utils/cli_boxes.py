"""
CLI boxes utility module.

Provides box drawing characters for terminal UIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

BoxStyleName = Literal[
    "single",
    "double",
    "round",
    "bold",
    "singleDouble",
    "doubleSingle",
    "classic",
    "arrow",
]


@dataclass(frozen=True)
class BoxStyle:
    """Box drawing style."""

    top_left: str
    top: str
    top_right: str
    right: str
    bottom_right: str
    bottom: str
    bottom_left: str
    left: str


# Box styles
BOXES: dict[BoxStyleName, BoxStyle] = {
    "single": BoxStyle(
        top_left="┌",
        top="─",
        top_right="┐",
        right="│",
        bottom_right="┘",
        bottom="─",
        bottom_left="└",
        left="│",
    ),
    "double": BoxStyle(
        top_left="╔",
        top="═",
        top_right="╗",
        right="║",
        bottom_right="╝",
        bottom="═",
        bottom_left="╚",
        left="║",
    ),
    "round": BoxStyle(
        top_left="╭",
        top="─",
        top_right="╮",
        right="│",
        bottom_right="╯",
        bottom="─",
        bottom_left="╰",
        left="│",
    ),
    "bold": BoxStyle(
        top_left="┏",
        top="━",
        top_right="┓",
        right="┃",
        bottom_right="┛",
        bottom="━",
        bottom_left="┗",
        left="┃",
    ),
    "singleDouble": BoxStyle(
        top_left="╓",
        top="─",
        top_right="╖",
        right="║",
        bottom_right="╜",
        bottom="─",
        bottom_left="╙",
        left="║",
    ),
    "doubleSingle": BoxStyle(
        top_left="╒",
        top="═",
        top_right="╕",
        right="│",
        bottom_right="╛",
        bottom="═",
        bottom_left="╘",
        left="│",
    ),
    "classic": BoxStyle(
        top_left="+",
        top="-",
        top_right="+",
        right="|",
        bottom_right="+",
        bottom="-",
        bottom_left="+",
        left="|",
    ),
    "arrow": BoxStyle(
        top_left="↘",
        top="↓",
        top_right="↙",
        right="←",
        bottom_right="↖",
        bottom="↑",
        bottom_left="↗",
        left="→",
    ),
}


def get_box_style(style: BoxStyleName | BoxStyle) -> BoxStyle:
    """
    Get a box style by name or return the style itself.

    Args:
        style: Either a style name or a BoxStyle instance.

    Returns:
        The BoxStyle instance.
    """
    if isinstance(style, BoxStyle):
        return style
    return BOXES[style]
