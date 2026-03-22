"""Virtual ANSI-aware output buffer."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from pyinkcli.ansi_tokenizer import tokenizeAnsi
from pyinkcli.sanitize_ansi import sanitizeAnsi
from pyinkcli.utils.string_width import string_width


@dataclass
class StyledCell:
    value: str
    styles: tuple[str, ...]
    suffix: str = ""


class Output:
    def __init__(self, options: dict[str, int]):
        self.width = int(options["width"])
        self.height = int(options["height"])
        self.operations: list[tuple[str, Any]] = []

    @staticmethod
    def _slice_ansi_columns(text: str, start: int, end: int) -> str:
        cells = Output._styled_cells(text)
        sliced = cells[start:end]
        return Output._styled_cells_to_string(sliced)

    @staticmethod
    def _styled_cells(text: str) -> list[StyledCell]:
        tokens = tokenizeAnsi(text)
        active_styles: list[str] = []
        cells: list[StyledCell] = []
        for token in tokens:
            if token.type == "csi":
                value = token.value
                if value in ("\x1b[0m", "\x1b[m"):
                    active_styles = []
                elif value.endswith("39m"):
                    active_styles = [style for style in active_styles if not (style.startswith("\x1b[3") or style.startswith("\x1b[9") or style.startswith("\x1b[38"))]
                elif value.endswith("49m"):
                    active_styles = [style for style in active_styles if not (style.startswith("\x1b[4") or style.startswith("\x1b[10") or style.startswith("\x1b[48"))]
                elif value.endswith("22m"):
                    active_styles = [style for style in active_styles if style not in ("\x1b[1m", "\x1b[2m")]
                elif value.endswith("23m"):
                    active_styles = [style for style in active_styles if style != "\x1b[3m"]
                elif value.endswith("24m"):
                    active_styles = [style for style in active_styles if style != "\x1b[4m"]
                elif value.endswith("27m"):
                    active_styles = [style for style in active_styles if style != "\x1b[7m"]
                elif value.endswith("29m"):
                    active_styles = [style for style in active_styles if style != "\x1b[9m"]
                elif value.endswith("m"):
                    params = value[2:-1]
                    first = params.split(";")[0] if params else ""
                    if first in {"30","31","32","33","34","35","36","37","90","91","92","93","94","95","96","97","38"}:
                        active_styles = [style for style in active_styles if not (style.startswith("\x1b[3") or style.startswith("\x1b[9") or style.startswith("\x1b[38"))]
                        active_styles.append(value)
                    elif first in {"40","41","42","43","44","45","46","47","100","101","102","103","104","105","106","107","48"}:
                        active_styles = [style for style in active_styles if not (style.startswith("\x1b[4") or style.startswith("\x1b[10") or style.startswith("\x1b[48"))]
                        active_styles.append(value)
                    else:
                        active_styles = [style for style in active_styles if style != value]
                        active_styles.append(value)
                continue
            if token.type != "text":
                continue
            for character in token.value:
                width = string_width(character)
                if width == 0 and cells:
                    cells[-1].suffix += character
                    continue
                styles = tuple(active_styles)
                cells.append(StyledCell(value=character, styles=styles))
        return cells

    @staticmethod
    def _styled_cells_to_string(cells: list[StyledCell]) -> str:
        pieces: list[str] = []
        current_styles: tuple[str, ...] = ()

        def _reset_codes(styles: tuple[str, ...], target: tuple[str, ...]) -> list[str]:
            resets: list[str] = []
            current_has_fg = any(style.startswith("\x1b[3") or style.startswith("\x1b[9") or style.startswith("\x1b[38") for style in styles)
            target_has_fg = any(style.startswith("\x1b[3") or style.startswith("\x1b[9") or style.startswith("\x1b[38") for style in target)
            if current_has_fg and not target_has_fg:
                resets.append("\x1b[39m")
            current_has_bg = any(style.startswith("\x1b[4") or style.startswith("\x1b[10") or style.startswith("\x1b[48") for style in styles)
            target_has_bg = any(style.startswith("\x1b[4") or style.startswith("\x1b[10") or style.startswith("\x1b[48") for style in target)
            if current_has_bg and not target_has_bg:
                resets.append("\x1b[49m")
            if any(style in ("\x1b[1m", "\x1b[2m") for style in styles):
                resets.append("\x1b[22m")
            if "\x1b[3m" in styles:
                resets.append("\x1b[23m")
            if "\x1b[4m" in styles:
                resets.append("\x1b[24m")
            if "\x1b[7m" in styles:
                resets.append("\x1b[27m")
            if "\x1b[9m" in styles:
                resets.append("\x1b[29m")
            return resets

        for cell in cells:
            target_styles = cell.styles
            if current_styles != target_styles:
                for reset in _reset_codes(tuple(style for style in current_styles if style not in target_styles), target_styles):
                    pieces.append(reset)
                for style in target_styles:
                    if style not in current_styles:
                        pieces.append(style)
                current_styles = target_styles
            pieces.append(cell.value)
            if cell.suffix:
                pieces.append(cell.suffix)
        for reset in _reset_codes(current_styles, ()):
            pieces.append(reset)
        return "".join(pieces)

    def write(self, x: int, y: int, text: str, options: dict[str, Any]) -> None:
        self.operations.append(("write", x, y, text, list(options.get("transformers", []))))

    def clip(self, clip: dict[str, int | None]) -> None:
        self.operations.append(("clip", clip))

    def unclip(self) -> None:
        self.operations.append(("unclip", None))

    def get(self):
        grid: list[list[StyledCell]] = [
            [StyledCell(" ", ()) for _ in range(self.width)]
            for _ in range(self.height)
        ]
        clips: list[dict[str, int | None]] = []
        for operation in self.operations:
            if operation[0] == "clip":
                clips.append(operation[1])
                continue
            if operation[0] == "unclip":
                if clips:
                    clips.pop()
                continue
            _, x, y, text, transformers = operation
            lines = str(text).split("\n")
            clip = clips[-1] if clips else None
            for line_index, raw_line in enumerate(lines):
                for transformer in transformers:
                    raw_line = sanitizeAnsi(transformer(raw_line, line_index))
                cells = self._styled_cells(raw_line)
                target_y = y + line_index
                if target_y < 0 or target_y >= self.height:
                    continue
                target_x = x
                for cell in cells:
                    if target_x >= self.width:
                        break
                    cell_width = max(1, string_width(cell.value))
                    if target_x >= 0:
                        if clip:
                            if clip.get("x1") is not None and target_x < clip["x1"]:
                                target_x += cell_width
                                continue
                            if clip.get("x2") is not None and target_x >= clip["x2"]:
                                break
                            if clip.get("y1") is not None and target_y < clip["y1"]:
                                continue
                            if clip.get("y2") is not None and target_y >= clip["y2"]:
                                continue
                        existing_cell = grid[target_y][target_x]
                        merged_styles = list(cell.styles)
                        has_bg = any(style.startswith("\x1b[4") or style.startswith("\x1b[10") or style.startswith("\x1b[48") for style in merged_styles)
                        if not has_bg:
                            for style in existing_cell.styles:
                                if style.startswith("\x1b[4") or style.startswith("\x1b[10") or style.startswith("\x1b[48"):
                                    merged_styles.append(style)
                        grid[target_y][target_x] = StyledCell(cell.value, tuple(merged_styles), cell.suffix)
                        if cell_width > 1:
                            for offset in range(1, cell_width):
                                if target_x + offset < self.width:
                                    grid[target_y][target_x + offset] = StyledCell("", tuple(merged_styles))
                    target_x += cell_width
        rendered_lines = [self._styled_cells_to_string(row).rstrip() for row in grid]
        return SimpleNamespace(output="\n".join(rendered_lines).rstrip("\n"), height=self.height)
