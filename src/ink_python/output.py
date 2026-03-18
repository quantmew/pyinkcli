"""
Output buffer for ink-python.

Tracks a virtual terminal surface using styled cells instead of plain strings,
which keeps ANSI styling, clipping, and full-width character handling stable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Union

from ink_python.ansi_tokenizer import tokenizeAnsi
from ink_python.sanitize_ansi import sanitizeAnsi
from ink_python.utils.string_width import string_width, widest_line

__all__ = ["Output"]


class _StyledChar:
    __slots__ = ("value", "width", "styles", "prefix", "suffix", "placeholder")
    pass

def _styled_char(
    value: str,
    width: int = 1,
    styles: tuple[str, ...] = (),
    prefix: str = "",
    suffix: str = "",
    placeholder: bool = False,
) -> "_StyledChar":
    cell = object.__new__(_StyledChar)
    cell.value = value
    cell.width = width
    cell.styles = styles
    cell.prefix = prefix
    cell.suffix = suffix
    cell.placeholder = placeholder
    return cell


def _placeholder_char() -> "_StyledChar":
    return _styled_char(value="", width=0, placeholder=True)


def _clone_styled_char(cell: "_StyledChar") -> "_StyledChar":
    return _styled_char(
        value=cell.value,
        width=cell.width,
        styles=cell.styles,
        prefix=cell.prefix,
        suffix=cell.suffix,
        placeholder=cell.placeholder,
    )


def _clone_styled_chars(cells: "_StyledLine") -> "_StyledLine":
    return [_clone_styled_char(cell) for cell in cells]


def _is_zero_width(cell: "_StyledChar") -> bool:
    return cell.width == 0


def _has_styled_payload(cell: "_StyledChar") -> bool:
    return bool(cell.styles or cell.prefix or cell.suffix)


def _styled_payload(cell: "_StyledChar") -> str:
    return cell.prefix + cell.value + cell.suffix


def _append_suffix_payload(cell: "_StyledChar", payload: str) -> None:
    cell.suffix += payload


def _append_pending_prefix(cells: "_StyledLine", pending_prefix: str) -> None:
    if not pending_prefix:
        return
    if cells:
        _append_suffix_payload(cells[-1], pending_prefix)
    else:
        cells.append(_styled_char(value="", width=0, prefix=pending_prefix))


def _append_zero_width(
    *,
    cells: "_StyledLine",
    output: "_StyledLine",
    cell: "_StyledChar",
    allow_leading_output: bool = False,
) -> None:
    payload = _styled_payload(cell)
    if output:
        _append_suffix_payload(output[-1], payload)
        return
    if allow_leading_output:
        output.append(_clone_styled_char(cell))
        return
    if cells:
        _append_suffix_payload(cells[-1], payload)


_StyledLine = list["_StyledChar"]
_StyledCharCache = dict[str, _StyledLine]


class Output:
    """Virtual output buffer for terminal rendering."""

    @dataclass
    class _ClipRegion:
        x1: Optional[int] = None
        x2: Optional[int] = None
        y1: Optional[int] = None
        y2: Optional[int] = None

    @dataclass
    class _WriteOperation:
        x: int
        y: int
        text: str
        transformers: list[Callable[[str, int], str]]

    @dataclass
    class _ClipOperation:
        clip: "Output._ClipRegion"

    @dataclass
    class _UnclipOperation:
        pass

    @staticmethod
    def _blank_cell() -> "_StyledChar":
        return _styled_char(value=" ")

    @staticmethod
    def _styled_cells(
        line: str,
        styled_cell_cache: Optional[_StyledCharCache] = None,
    ) -> _StyledLine:
        if styled_cell_cache is not None:
            cached = styled_cell_cache.get(line)
            if cached is None:
                cached = Output._styled_cells_uncached(line)
                styled_cell_cache[line] = _clone_styled_chars(cached)
                return cached
            return _clone_styled_chars(cached)
        return Output._styled_cells_uncached(line)

    @staticmethod
    def _styled_cells_uncached(line: str) -> _StyledLine:
        cells: _StyledLine = []
        pending_prefix = ""
        active_styles: list[str] = []

        for token in tokenizeAnsi(line):
            if token.type == "text":
                for char in token.value:
                    width = max(0, string_width(char))
                    if width == 0:
                        _append_zero_width(
                            cells=cells,
                            output=[],
                            cell=_styled_char(value=char, width=0, prefix=pending_prefix),
                        )
                        pending_prefix = ""
                        continue

                    cells.append(
                        _styled_char(
                            value=char,
                            width=width,
                            styles=tuple(active_styles),
                            prefix=pending_prefix,
                        )
                    )
                    pending_prefix = ""
                continue

            if Output._is_sgr_token(token.value):
                active_styles = Output._apply_sgr_token(active_styles, token.value)
            else:
                pending_prefix += token.value

        _append_pending_prefix(cells, pending_prefix)

        return cells

    @staticmethod
    def _slice_ansi_columns(
        text: str,
        start: int,
        end: int,
        *,
        styled_cell_cache: Optional[_StyledCharCache] = None,
    ) -> str:
            if end <= start:
                return ""

            visible = 0
            output: _StyledLine = []
            saw_ansi = False

            for cell in Output._styled_cells(text, styled_cell_cache=styled_cell_cache):
                if _has_styled_payload(cell):
                    saw_ansi = True

                token_width = max(0, cell.width)
                if _is_zero_width(cell):
                    _append_zero_width(
                        cells=[],
                        output=output,
                        cell=cell,
                        allow_leading_output=start == 0,
                    )
                    continue

                next_visible = visible + token_width
                if next_visible <= start:
                    visible = next_visible
                    continue

                if visible >= end:
                    break

                output.append(_clone_styled_char(cell))
                visible = next_visible
                if visible >= end:
                    break

            result = Output._styled_cells_to_string(output)
            if saw_ansi and result and not Output._ends_with_sgr_reset(result):
                result += "\x1b[0m"
            return result

    @staticmethod
    def _write_ansi_line(
        row: _StyledLine,
        x: int,
        line: str,
        *,
        styled_cell_cache: Optional[_StyledCharCache] = None,
    ) -> None:
            offset_x = x
            for cell in Output._styled_cells(line, styled_cell_cache=styled_cell_cache):
                if _is_zero_width(cell):
                    if 0 <= offset_x - 1 < len(row):
                        _append_suffix_payload(row[offset_x - 1], _styled_payload(cell))
                    continue

                if offset_x >= len(row):
                    break

                if offset_x >= 0:
                    row[offset_x] = Output._merge_cells(row[offset_x], cell)
                    for width_index in range(1, cell.width):
                        if offset_x + width_index < len(row):
                            row[offset_x + width_index] = _placeholder_char()

                offset_x += cell.width

    @staticmethod
    def _styled_cells_to_string(cells: _StyledLine) -> str:
            output: list[str] = []
            previous_styles: tuple[str, ...] = ()
            for cell in cells:
                if cell.placeholder:
                    continue
                if cell.styles != previous_styles:
                    output.append(Output._style_transition(previous_styles, cell.styles))
                    previous_styles = cell.styles
                output.append(cell.prefix + cell.value + cell.suffix)

            if previous_styles:
                output.append(Output._reset_for_styles(previous_styles))

            return "".join(output)

    @staticmethod
    def _ends_with_sgr_reset(text: str) -> bool:
            for token in reversed(tokenizeAnsi(text)):
                if token.type == "text":
                    continue
                if token.value.endswith("[0m") or token.value.endswith("[39m") or token.value.endswith("[49m"):
                    return True
                break
            return False

    @staticmethod
    def _is_sgr_token(token: str) -> bool:
        return token.startswith("\x1b[") and token.endswith("m")

    @staticmethod
    def _apply_sgr_token(active_styles: list[str], token: str) -> list[str]:
        body = token[2:-1]
        codes = ["0"] if body == "" else Output._parse_sgr_parameters(body.split(";"))
        next_styles = list(active_styles)

        for code in codes:
            if code == "0":
                next_styles.clear()
                continue
            if code == "39":
                next_styles = [style for style in next_styles if not Output._is_foreground_style(style)]
                continue
            if code == "49":
                next_styles = [style for style in next_styles if not Output._is_background_style(style)]
                continue
            if code == "22":
                next_styles = [style for style in next_styles if style not in ("\x1b[1m", "\x1b[2m")]
                continue
            if code == "23":
                next_styles = [style for style in next_styles if style != "\x1b[3m"]
                continue
            if code == "24":
                next_styles = [style for style in next_styles if style != "\x1b[4m"]
                continue
            if code == "29":
                next_styles = [style for style in next_styles if style != "\x1b[9m"]
                continue

            style_escape = f"\x1b[{code}m"
            if Output._is_foreground_code(code):
                next_styles = [style for style in next_styles if not Output._is_foreground_style(style)]
            elif Output._is_background_code(code):
                next_styles = [style for style in next_styles if not Output._is_background_style(style)]
            next_styles.append(style_escape)

        return next_styles

    @staticmethod
    def _style_transition(previous_styles: tuple[str, ...], next_styles: tuple[str, ...]) -> str:
            if previous_styles == next_styles:
                return ""

            previous_foreground = Output._extract_foreground_style(previous_styles)
            next_foreground = Output._extract_foreground_style(next_styles)
            previous_background = Output._extract_background_style(previous_styles)
            next_background = Output._extract_background_style(next_styles)
            previous_other = Output._extract_other_styles(previous_styles)
            next_other = Output._extract_other_styles(next_styles)

            if previous_other != next_other:
                return Output._reset_for_styles(previous_styles) + "".join(next_styles)

            transition: list[str] = []
            if previous_foreground != next_foreground:
                transition.append(next_foreground if next_foreground else "\x1b[39m")
            if previous_background != next_background:
                transition.append(next_background if next_background else "\x1b[49m")
            return "".join(transition)

    @staticmethod
    def _is_foreground_code(code: str) -> bool:
            return (
                code in {str(value) for value in range(30, 38)}
                or code in {"90", "91", "92", "93", "94", "95", "96", "97"}
                or code.startswith("38;")
            )

    @staticmethod
    def _is_background_code(code: str) -> bool:
            return (
                code in {str(value) for value in range(40, 48)}
                or code in {"100", "101", "102", "103", "104", "105", "106", "107"}
                or code.startswith("48;")
            )

    @staticmethod
    def _is_foreground_style(style: str) -> bool:
        return Output._is_sgr_token(style) and Output._is_foreground_code(style[2:-1])

    @staticmethod
    def _is_background_style(style: str) -> bool:
        return Output._is_sgr_token(style) and Output._is_background_code(style[2:-1])

    @staticmethod
    def _merge_cells(
        existing: "_StyledChar",
        incoming: "_StyledChar",
    ) -> "_StyledChar":
            merged = _clone_styled_char(incoming)
            if not any(Output._is_background_style(style) for style in merged.styles):
                inherited_background = tuple(
                    style for style in existing.styles if Output._is_background_style(style)
                )
                if inherited_background:
                    merged.styles = tuple(
                        style for style in merged.styles if not Output._is_background_style(style)
                    ) + inherited_background
            return merged

    @staticmethod
    def _extract_foreground_style(styles: tuple[str, ...]) -> str | None:
            for style in styles:
                if Output._is_foreground_style(style):
                    return style
            return None

    @staticmethod
    def _extract_background_style(styles: tuple[str, ...]) -> str | None:
            for style in styles:
                if Output._is_background_style(style):
                    return style
            return None

    @staticmethod
    def _extract_other_styles(styles: tuple[str, ...]) -> tuple[str, ...]:
            return tuple(
                style
                for style in styles
                if not Output._is_foreground_style(style) and not Output._is_background_style(style)
            )

    @staticmethod
    def _reset_for_styles(styles: tuple[str, ...]) -> str:
            other_resets: list[str] = []
            for style in reversed(Output._extract_other_styles(styles)):
                other_resets.extend(Output._reset_sequence_for_style(style))

            foreground = Output._extract_foreground_style(styles)
            background = Output._extract_background_style(styles)
            resets = other_resets
            if foreground:
                resets.append("\x1b[39m")
            if background:
                resets.append("\x1b[49m")
            return "".join(resets) if resets else ""

    @staticmethod
    def _reset_sequence_for_style(style: str) -> list[str]:
            mapping = {
                "\x1b[1m": ["\x1b[22m"],
                "\x1b[2m": ["\x1b[22m"],
                "\x1b[3m": ["\x1b[23m"],
                "\x1b[4m": ["\x1b[24m"],
                "\x1b[7m": ["\x1b[27m"],
                "\x1b[9m": ["\x1b[29m"],
            }
            return mapping.get(style, ["\x1b[0m"])

    @staticmethod
    def _parse_sgr_parameters(parameters: list[str]) -> list[str]:
            grouped: list[str] = []
            index = 0
            while index < len(parameters):
                code = parameters[index]
                if code in {"38", "48", "58"} and index + 1 < len(parameters):
                    mode = parameters[index + 1]
                    if mode == "5" and index + 2 < len(parameters):
                        grouped.append(";".join(parameters[index:index + 3]))
                        index += 3
                        continue
                    if mode == "2" and index + 4 < len(parameters):
                        grouped.append(";".join(parameters[index:index + 5]))
                        index += 5
                        continue
                grouped.append(code)
                index += 1
            return grouped

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self._operations: list[
            Union[Output._WriteOperation, Output._ClipOperation, Output._UnclipOperation]
        ] = []
        self._width_cache: dict[str, int] = {}
        self._block_width_cache: dict[str, int] = {}
        self._styled_cell_cache: _StyledCharCache = {}

    def _get_string_width(self, text: str) -> int:
        cached = self._width_cache.get(text)
        if cached is None:
            cached = string_width(text)
            self._width_cache[text] = cached
        return cached

    def _get_widest_line(self, text: str) -> int:
        cached = self._block_width_cache.get(text)
        if cached is None:
            cached = widest_line(text)
            self._block_width_cache[text] = cached
        return cached

    def write(
        self,
        x: int,
        y: int,
        text: str,
        transformers: Optional[list[Callable[[str, int], str]]] = None,
    ) -> None:
        text = sanitizeAnsi(text)
        if not text:
            return

        self._operations.append(
            Output._WriteOperation(
                x=x,
                y=y,
                text=text,
                transformers=transformers or [],
            )
        )

    def clip(
        self,
        x1: Optional[int] = None,
        x2: Optional[int] = None,
        y1: Optional[int] = None,
        y2: Optional[int] = None,
    ) -> None:
        self._operations.append(
            Output._ClipOperation(
                clip=Output._ClipRegion(x1=x1, x2=x2, y1=y1, y2=y2)
            )
        )

    def unclip(self) -> None:
        self._operations.append(Output._UnclipOperation())

    def get(self) -> tuple[str, int]:
        rows = [[Output._blank_cell() for _ in range(self.width)] for _ in range(self.height)]
        clips: list[Output._ClipRegion] = []

        for operation in self._operations:
            if isinstance(operation, Output._ClipOperation):
                clips.append(operation.clip)
                continue

            if isinstance(operation, Output._UnclipOperation):
                if clips:
                    clips.pop()
                continue

            self._apply_write(rows, operation, clips[-1] if clips else None)

        lines = [
            Output._styled_cells_to_string([cell for cell in row if not cell.placeholder]).rstrip()
            for row in rows
        ]
        return ("\n".join(lines), len(rows))

    def _apply_write(
        self,
        rows: list[_StyledLine],
        operation: "Output._WriteOperation",
        clip: Optional["Output._ClipRegion"],
    ) -> None:
        x = operation.x
        y = operation.y
        lines = operation.text.split("\n")

        if clip is not None:
            if clip.x1 is not None and clip.x2 is not None:
                width = self._get_widest_line(operation.text)
                if x + width < clip.x1 or x > clip.x2:
                    return

            if clip.y1 is not None and clip.y2 is not None:
                height = len(lines)
                if y + height < clip.y1 or y > clip.y2:
                    return

            if clip.x1 is not None and clip.x2 is not None:
                clipped_lines: list[str] = []
                for line in lines:
                    start = clip.x1 - x if x < clip.x1 else 0
                    width = self._get_string_width(line)
                    end = clip.x2 - x if x + width > clip.x2 else width
                    clipped_lines.append(
                        Output._slice_ansi_columns(
                            line,
                            start,
                            end,
                            styled_cell_cache=self._styled_cell_cache,
                        )
                    )
                lines = clipped_lines
                if x < clip.x1:
                    x = clip.x1

            if clip.y1 is not None and clip.y2 is not None:
                start = clip.y1 - y if y < clip.y1 else 0
                height = len(lines)
                end = clip.y2 - y if y + height > clip.y2 else height
                lines = lines[start:end]
                if y < clip.y1:
                    y = clip.y1

        for row_offset, line in enumerate(lines):
            row_index = y + row_offset
            if row_index < 0 or row_index >= len(rows):
                continue

            for transformer in operation.transformers:
                line = transformer(line, row_offset)

            line = sanitizeAnsi(line)
            Output._write_ansi_line(
                rows[row_index],
                x,
                line,
                styled_cell_cache=self._styled_cell_cache,
            )
