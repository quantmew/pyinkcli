from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from .ansi_tokenizer import tokenizeAnsi
from .sanitize_ansi import sanitizeAnsi
from .utils.string_width import string_width


@dataclass
class StyledCell:
    char: str
    styles: tuple[str, ...]
    suffix: str = ""


def _style_category(sequence: str) -> str | None:
    token = tokenizeAnsi(sequence)[0]
    if token.type != "csi" or token.final_character != "m":
        return None
    params = token.parameter_string
    if params == "0":
        return "reset"
    if params == "39" or params.startswith("38;") or params in {str(code) for code in range(30, 38)} | {str(code) for code in range(90, 98)}:
        return "fg"
    if params == "49" or params.startswith("48;") or params in {str(code) for code in range(40, 48)} | {str(code) for code in range(100, 108)}:
        return "bg"
    return None


class Output:
    def __init__(self, dimensions: dict[str, int]) -> None:
        self.width = dimensions["width"]
        self.height = dimensions["height"]
        self._rows: list[list[StyledCell | None]] = [[None for _ in range(self.width)] for _ in range(self.height)]
        self._clip = {"x1": 0, "x2": self.width}

    @staticmethod
    def _styled_cells(text: str) -> list[StyledCell]:
        sanitized = sanitizeAnsi(text)
        tokens = tokenizeAnsi(sanitized)
        styles: list[str] = []
        cells: list[StyledCell] = []
        for token in tokens:
            if token.type == "csi" and token.final_character == "m":
                category = _style_category(token.value)
                if category == "reset":
                    styles.clear()
                elif category == "fg":
                    styles = [style for style in styles if _style_category(style) != "fg"]
                    if token.parameter_string != "39":
                        styles.append(token.value)
                elif category == "bg":
                    styles = [style for style in styles if _style_category(style) != "bg"]
                    if token.parameter_string != "49":
                        styles.append(token.value)
                continue
            if token.type != "text":
                continue
            for character in token.value:
                width = string_width(character)
                if width == 0 and cells:
                    cells[-1].suffix += character
                    continue
                cells.append(StyledCell(character, tuple(styles)))
        return cells

    @staticmethod
    def _styled_cells_to_string(cells: list[StyledCell]) -> str:
        output: list[str] = []
        current_styles: tuple[str, ...] = ()
        for cell in cells:
            if cell.styles != current_styles:
                previous_categories = {_style_category(style) for style in current_styles}
                next_categories = {_style_category(style) for style in cell.styles}
                if "fg" in previous_categories and "fg" not in next_categories:
                    output.append("\x1b[39m")
                if "bg" in previous_categories and "bg" not in next_categories:
                    output.append("\x1b[49m")
                for style in cell.styles:
                    if style not in current_styles:
                        output.append(style)
                current_styles = cell.styles
            output.append(cell.char + cell.suffix)
        if any(_style_category(style) == "fg" for style in current_styles):
            output.append("\x1b[39m")
        if any(_style_category(style) == "bg" for style in current_styles):
            output.append("\x1b[49m")
        return "".join(output)

    @staticmethod
    def _slice_ansi_columns(text: str, start: int, end: int) -> str:
        cells = Output._styled_cells(text)
        sliced: list[StyledCell] = []
        column = 0
        for cell in cells:
            width = max(string_width(cell.char), 1)
            if column + width <= start:
                column += width
                continue
            if column >= end:
                break
            sliced.append(cell)
            column += width
        return Output._styled_cells_to_string(sliced)

    def clip(self, bounds: dict[str, int]) -> None:
        self._clip = bounds

    def unclip(self) -> None:
        self._clip = {"x1": 0, "x2": self.width}

    def write(self, x: int, y: int, text: str, options: dict[str, Any]) -> None:
        rendered = sanitizeAnsi(text)
        for index, transformer in enumerate(options.get("transformers", [])):
            rendered = sanitizeAnsi(transformer(rendered, index))
        rendered = self._slice_ansi_columns(rendered, self._clip["x1"], self._clip["x2"])
        cells = self._styled_cells(rendered)
        column = x
        for cell in cells:
            if 0 <= y < self.height and 0 <= column < self.width:
                self._rows[y][column] = cell
            column += max(string_width(cell.char), 1)

    def get(self):
        lines = []
        for row in self._rows:
            cells = [cell for cell in row if cell is not None]
            lines.append(self._styled_cells_to_string(cells))
        return SimpleNamespace(output="\n".join(lines).rstrip("\n"))


__all__ = ["Output"]
