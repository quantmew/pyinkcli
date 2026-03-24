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
    width: int = 1


def _style_category(sequence: str) -> str | None:
    token = tokenizeAnsi(sequence)[0]
    if token.type != "csi" or token.final_character != "m":
        return None
    params = token.parameter_string
    if params == "0":
        return "reset"
    if params in {"1", "2", "22"}:
        return "intensity"
    if params in {"4", "24"}:
        return "underline"
    if params in {"7", "27"}:
        return "inverse"
    if params == "39" or params.startswith("38;") or params in {str(code) for code in range(30, 38)} | {str(code) for code in range(90, 98)}:
        return "fg"
    if params == "49" or params.startswith("48;") or params in {str(code) for code in range(40, 48)} | {str(code) for code in range(100, 108)}:
        return "bg"
    return None


class Output:
    _styled_cells_cache: dict[str, tuple[StyledCell, ...]] = {}

    def __init__(self, dimensions: dict[str, int]) -> None:
        self.width = dimensions["width"]
        self.height = dimensions["height"]
        self._operations: list[dict[str, Any]] = []
        self._cached_result = None

    @staticmethod
    def _styled_cells(text: str) -> list[StyledCell]:
        sanitized = sanitizeAnsi(text)
        cached = Output._styled_cells_cache.get(sanitized)
        if cached is not None:
            return list(cached)
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
                elif category == "intensity":
                    styles = [style for style in styles if _style_category(style) != "intensity"]
                    if token.parameter_string != "22":
                        styles.append(token.value)
                elif category == "underline":
                    styles = [style for style in styles if _style_category(style) != "underline"]
                    if token.parameter_string != "24":
                        styles.append(token.value)
                elif category == "inverse":
                    styles = [style for style in styles if _style_category(style) != "inverse"]
                    if token.parameter_string != "27":
                        styles.append(token.value)
                continue
            if token.type != "text":
                continue
            for character in token.value:
                if character == "\n":
                    cells.append(StyledCell(character, tuple(styles), width=0))
                    continue
                width = string_width(character)
                if width == 0 and cells:
                    cells[-1].suffix += character
                    continue
                cells.append(StyledCell(character, tuple(styles), width=max(width, 1)))
        if len(Output._styled_cells_cache) > 4096:
            Output._styled_cells_cache.clear()
        Output._styled_cells_cache[sanitized] = tuple(cells)
        return cells

    @staticmethod
    def _styled_cells_to_string(cells: list[StyledCell]) -> str:
        def append_resets(previous_categories: set[str | None], next_categories: set[str | None]) -> list[str]:
            resets: list[str] = []
            if "fg" in previous_categories and "fg" not in next_categories:
                resets.append("\x1b[39m")
            if "bg" in previous_categories and "bg" not in next_categories:
                resets.append("\x1b[49m")
            if "intensity" in previous_categories and "intensity" not in next_categories:
                resets.append("\x1b[22m")
            if "underline" in previous_categories and "underline" not in next_categories:
                resets.append("\x1b[24m")
            if "inverse" in previous_categories and "inverse" not in next_categories:
                resets.append("\x1b[27m")
            return resets

        output: list[str] = []
        current_styles: tuple[str, ...] = ()
        for cell in cells:
            if cell.styles != current_styles:
                previous_categories = {_style_category(style) for style in current_styles}
                next_categories = {_style_category(style) for style in cell.styles}
                output.extend(append_resets(previous_categories, next_categories))
                for style in cell.styles:
                    if style not in current_styles:
                        output.append(style)
                current_styles = cell.styles
            output.append(cell.char + cell.suffix)
        output.extend(append_resets({_style_category(style) for style in current_styles}, set()))
        return "".join(output)

    @staticmethod
    def _slice_ansi_columns(text: str, start: int, end: int) -> str:
        cells = Output._styled_cells(text)
        sliced = Output._slice_cells_columns(cells, start, end)
        return Output._styled_cells_to_string(sliced)

    @staticmethod
    def _slice_cells_columns(cells: tuple[StyledCell, ...] | list[StyledCell], start: int, end: int) -> list[StyledCell]:
        sliced: list[StyledCell] = []
        column = 0
        for cell in cells:
            width = cell.width
            if column + width <= start:
                column += width
                continue
            if column >= end:
                break
            sliced.append(cell)
            column += width
        return sliced

    @staticmethod
    def _visible_width(text: str) -> int:
        return sum(cell.width for cell in Output._styled_cells(text))

    def clip(self, bounds: dict[str, int]) -> None:
        self._cached_result = None
        self._operations.append({"type": "clip", "clip": bounds})

    def unclip(self) -> None:
        self._cached_result = None
        self._operations.append({"type": "unclip"})

    def write(self, x: int, y: int, text: str, options: dict[str, Any]) -> None:
        if not text:
            return
        self._cached_result = None
        transformers = list(options.get("transformers", []))
        sanitized = text if options.get("sanitized") else sanitizeAnsi(text)
        lines = tuple(sanitized.split("\n"))
        prepared_cells = None
        if not transformers:
            prepared_cells = tuple(Output._styled_cells(line) for line in lines)
        self._operations.append(
            {
                "type": "write",
                "x": x,
                "y": y,
                "text": sanitized,
                "lines": lines,
                "line_widths": tuple(sum(cell.width for cell in line) for line in prepared_cells)
                if prepared_cells is not None
                else tuple(self._visible_width(line) for line in lines),
                "prepared_cells": prepared_cells,
                "transformers": transformers,
            }
        )

    def get(self):
        if self._cached_result is not None:
            return self._cached_result
        rows: list[list[StyledCell | None]] = [[None for _ in range(self.width)] for _ in range(self.height)]
        clips: list[dict[str, int | None]] = []

        for operation in self._operations:
            if operation["type"] == "clip":
                clips.append(operation["clip"])
                continue

            if operation["type"] == "unclip":
                if clips:
                    clips.pop()
                continue

            x = operation["x"]
            y = operation["y"]
            lines = list(operation["lines"])
            line_widths = list(operation["line_widths"])
            prepared_cells = operation["prepared_cells"]
            clip = clips[-1] if clips else None

            if clip:
                clip_horizontally = clip.get("x1") is not None and clip.get("x2") is not None
                clip_vertically = clip.get("y1") is not None and clip.get("y2") is not None

                if clip_horizontally:
                    widest = max(line_widths, default=0)
                    if x + widest < clip["x1"] or x > clip["x2"]:
                        continue

                if clip_vertically:
                    height = len(lines)
                    if y + height < clip["y1"] or y > clip["y2"]:
                        continue

                if clip_horizontally:
                    sliced_lines = []
                    sliced_cells = [] if prepared_cells is not None else None
                    sliced_widths = []
                    for index, line in enumerate(lines):
                        width = line_widths[index]
                        start = clip["x1"] - x if x < clip["x1"] else 0
                        end = clip["x2"] - x if x + width > clip["x2"] else width
                        start = max(start, 0)
                        end = max(end, 0)
                        if prepared_cells is not None:
                            line_cells = self._slice_cells_columns(prepared_cells[index], start, end)
                            sliced_cells.append(tuple(line_cells))
                            sliced_widths.append(sum(cell.width for cell in line_cells))
                            sliced_lines.append(self._styled_cells_to_string(line_cells))
                        else:
                            sliced_line = self._slice_ansi_columns(line, start, end)
                            sliced_lines.append(sliced_line)
                            sliced_widths.append(self._visible_width(sliced_line))
                    lines = sliced_lines
                    line_widths = sliced_widths
                    if sliced_cells is not None:
                        prepared_cells = tuple(sliced_cells)
                    if x < clip["x1"]:
                        x = clip["x1"]

                if clip_vertically:
                    start = clip["y1"] - y if y < clip["y1"] else 0
                    end = clip["y2"] - y if y + len(lines) > clip["y2"] else len(lines)
                    lines = lines[max(start, 0) : max(end, 0)]
                    line_widths = line_widths[max(start, 0) : max(end, 0)]
                    if prepared_cells is not None:
                        prepared_cells = prepared_cells[max(start, 0) : max(end, 0)]
                    if y < clip["y1"]:
                        y = clip["y1"]

            for line_index, line in enumerate(lines):
                row_y = y + line_index
                if not (0 <= row_y < self.height):
                    continue

                rendered = line
                for transformer in operation["transformers"]:
                    rendered = sanitizeAnsi(transformer(rendered, line_index))

                if prepared_cells is not None and not operation["transformers"]:
                    cells = prepared_cells[line_index]
                else:
                    cells = self._styled_cells(rendered)
                column = x
                for cell in cells:
                    cell_width = cell.width
                    if 0 <= column < self.width:
                        rows[row_y][column] = cell
                        for offset in range(1, cell_width):
                            if column + offset < self.width:
                                rows[row_y][column + offset] = StyledCell("", cell.styles, width=1)
                    column += cell_width

        lines = []
        for row in rows:
            last_index = -1
            for index, cell in enumerate(row):
                if cell is not None:
                    last_index = index
            if last_index == -1:
                lines.append("")
                continue
            cells = [cell if cell is not None else StyledCell(" ", (), width=1) for cell in row[: last_index + 1]]
            lines.append(self._styled_cells_to_string(cells))
        self._cached_result = SimpleNamespace(output="\n".join(lines).rstrip("\n"), height=len(rows))
        return self._cached_result


__all__ = ["Output"]
