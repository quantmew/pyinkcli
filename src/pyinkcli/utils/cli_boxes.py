from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BoxStyle:
    top_left: str
    top: str
    top_right: str
    right: str
    bottom_right: str
    bottom: str
    bottom_left: str
    left: str


BOXES = {
    "single": BoxStyle("┌", "─", "┐", "│", "┘", "─", "└", "│"),
    "double": BoxStyle("╔", "═", "╗", "║", "╝", "═", "╚", "║"),
    "round": BoxStyle("╭", "─", "╮", "│", "╯", "─", "╰", "│"),
    "bold": BoxStyle("┏", "━", "┓", "┃", "┛", "━", "┗", "┃"),
    "singleDouble": BoxStyle("╓", "─", "╖", "║", "╜", "─", "╙", "║"),
    "doubleSingle": BoxStyle("╒", "═", "╕", "│", "╛", "═", "╘", "│"),
    "classic": BoxStyle("+", "-", "+", "|", "+", "-", "+", "|"),
    "arrow": BoxStyle("↘", "↓", "↙", "←", "↖", "↑", "↗", "→"),
}


def get_box_style(style: str | BoxStyle) -> BoxStyle:
    if isinstance(style, BoxStyle):
        return style
    return BOXES[style]


__all__ = ["BOXES", "BoxStyle", "get_box_style"]
