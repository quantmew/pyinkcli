from __future__ import annotations

import contextlib
import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import yoga

from .components.Text import ANSI_BG_OPEN, ANSI_OPEN
from .colorize import color_sequence
from .output import Output, _style_category
from .squash_text_nodes import squashTextNodes
from .utils.cli_boxes import get_box_style
from .utils.string_width import string_width
from .utils.wrap_ansi import truncate_string, wrap_ansi
from .yoga_compat import (
    ALIGN_AUTO,
    ALIGN_CENTER,
    ALIGN_FLEX_END,
    ALIGN_FLEX_START,
    ALIGN_STRETCH,
    DIRECTION_LTR,
    EDGE_ALL,
    EDGE_BOTTOM,
    EDGE_LEFT,
    EDGE_RIGHT,
    EDGE_TOP,
    FLEX_DIRECTION_COLUMN,
    FLEX_DIRECTION_ROW,
    GUTTER_ALL,
    JUSTIFY_CENTER,
    JUSTIFY_FLEX_END,
    JUSTIFY_FLEX_START,
    JUSTIFY_SPACE_AROUND,
    JUSTIFY_SPACE_BETWEEN,
    JUSTIFY_SPACE_EVENLY,
    WRAP_NO_WRAP,
    WRAP_WRAP,
    Node,
)

LAYOUT_STYLE_KEYS = {
    "alignItems",
    "alignSelf",
    "backgroundColor",
    "background_color",
    "borderColor",
    "borderStyle",
    "display",
    "flexDirection",
    "flexGrow",
    "flexShrink",
    "flexWrap",
    "gap",
    "height",
    "justifyContent",
    "margin",
    "marginBottom",
    "marginLeft",
    "marginRight",
    "marginTop",
    "maxWidth",
    "minWidth",
    "overflow",
    "padding",
    "paddingBottom",
    "paddingLeft",
    "paddingRight",
    "paddingTop",
    "paddingX",
    "paddingY",
    "padding_x",
    "padding_y",
    "width",
}


@dataclass
class RenderedBlock:
    lines: list[str]
    width: int
    height: int

    def to_output(self) -> str:
        return "\n".join(self.lines).rstrip("\n")


def _numeric(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return float(stripped)
    return None


def _percent(value: Any) -> float | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped.endswith("%"):
        return None
    number = stripped[:-1].strip()
    try:
        return float(number)
    except ValueError:
        return None


def _int_value(value: Any, default: int = 0) -> int:
    numeric = _numeric(value)
    if numeric is None or math.isnan(numeric):
        return default
    return max(int(round(numeric)), 0)


def _node_style(node) -> dict[str, Any]:
    style = dict(getattr(node, "style", {}))
    style.update(getattr(node, "attributes", {}).get("style", {}))
    for key in LAYOUT_STYLE_KEYS:
        if key in getattr(node, "attributes", {}):
            style.setdefault(key, node.attributes[key])
    if "background_color" in style and "backgroundColor" not in style:
        style["backgroundColor"] = style["background_color"]
    if "paddingX" in style and "padding_x" not in style:
        style["padding_x"] = style["paddingX"]
    if "paddingY" in style and "padding_y" not in style:
        style["padding_y"] = style["paddingY"]
    return style


def _edge_values(style: dict[str, Any], prefix: str) -> dict[int, int]:
    base = _int_value(style.get(prefix, 0))
    horizontal = _int_value(style.get(f"{prefix}_x", style.get(f"{prefix}X", 0)))
    vertical = _int_value(style.get(f"{prefix}_y", style.get(f"{prefix}Y", 0)))
    return {
        EDGE_LEFT: base + horizontal + _int_value(style.get(f"{prefix}Left", 0)),
        EDGE_RIGHT: base + horizontal + _int_value(style.get(f"{prefix}Right", 0)),
        EDGE_TOP: base + vertical + _int_value(style.get(f"{prefix}Top", 0)),
        EDGE_BOTTOM: base + vertical + _int_value(style.get(f"{prefix}Bottom", 0)),
    }


def _background_sequence(name: str | None) -> str | None:
    if not name:
        return None
    if (sequence := color_sequence(name, "background")) is not None:
        return sequence
    return ANSI_BG_OPEN.get(name)


def _cells_width(cells) -> int:
    return sum(getattr(cell, "width", max(string_width(cell.char), 1)) for cell in cells)


def _recompute_last_space(current) -> int | None:
    for index in range(len(current) - 1, -1, -1):
        if current[index].char == " ":
            return index
    return None


def _wrap_cells(cells, limit: int | None) -> list[list]:
    if limit is not None and limit <= 0:
        limit = 1
    lines: list[list] = []
    current: list = []
    current_width = 0
    last_space_index: int | None = None

    for cell in cells:
        if cell.char == "\n":
            lines.append(current)
            current = []
            current_width = 0
            last_space_index = None
            continue

        cell_width = getattr(cell, "width", max(string_width(cell.char), 1))
        if limit is not None and current and current_width + cell_width > limit:
            if last_space_index is not None:
                lines.append(current[: last_space_index + 1])
                current = current[last_space_index + 1 :]
                current_width = _cells_width(current)
                last_space_index = _recompute_last_space(current)
            else:
                lines.append(current)
                current = []
                current_width = 0
                last_space_index = None

        current.append(cell)
        current_width += cell_width
        if cell.char == " ":
            last_space_index = len(current) - 1

    lines.append(current)
    return lines or [[]]


def _apply_background(cells, background: str | None):
    if background is None:
        return cells
    updated = []
    for cell in cells:
        if any(_style_category(style) == "bg" for style in cell.styles):
            updated.append(cell)
            continue
        updated.append(type(cell)(cell.char, (*cell.styles, background), cell.suffix, getattr(cell, "width", 1)))
    return updated


def _inline_text(node) -> str:
    node_name = getattr(node, "nodeName", None)
    if node_name == "#text":
        return getattr(node, "nodeValue", "")
    if node_name != "ink-text":
        return "".join(_inline_text(child) for child in getattr(node, "childNodes", []))
    content = "".join(_inline_text(child) for child in getattr(node, "childNodes", []))
    transform = getattr(node, "internal_transform", None)
    if transform is None:
        transform = getattr(node, "attributes", {}).get("internal_transform")
    return transform(content) if callable(transform) else content


def _text_content(node) -> str:
    if getattr(node, "nodeName", None) == "#text":
        return getattr(node, "nodeValue", "")
    if getattr(node, "nodeName", None) == "ink-text":
        return squashTextNodes(node)
    return "".join(_text_content(child) for child in getattr(node, "childNodes", []))


def _text_lines(node, width: int | None, inherited_background: str | None) -> tuple[list[str], int]:
    text = _text_content(node)
    cells = Output._styled_cells(text)
    wrapped = _wrap_cells(cells, width)
    lines = [Output._styled_cells_to_string(line) for line in wrapped]
    measured_width = max((_cells_width(line) for line in wrapped), default=0)
    return lines or [""], measured_width


@lru_cache(maxsize=4096)
def _wrap_text_value(text: str, max_width: int, wrap_type: str) -> str:
    if max_width <= 0:
        return text
    if wrap_type == "wrap":
        return wrap_ansi(text, max_width, hard=True)
    if wrap_type.startswith("truncate"):
        position = "end"
        if wrap_type == "truncate-middle":
            position = "middle"
        elif wrap_type == "truncate-start":
            position = "start"
        return truncate_string(text, max_width, position=position)
    return text


def _text_measure_signature(node, text: str) -> tuple[int, int, str]:
    text_wrap = _node_style(node).get("textWrap", "wrap")
    max_width = _get_max_width(node)
    if text_wrap == "wrap" and max_width > 0:
        wrapped_lines, measured_width = _text_lines(node, max_width, None)
        return len(wrapped_lines), measured_width, text_wrap
    wrapped_text = text
    if max_width > 0:
        current_width = max((string_width(line) for line in text.split("\n")), default=0)
        if current_width > max_width:
            wrapped_text = _wrap_text_value(text, max_width, text_wrap)
    wrapped_lines = wrapped_text.split("\n") if wrapped_text else [""]
    measured_width = max((string_width(line) for line in wrapped_lines), default=0)
    return len(wrapped_lines), measured_width, text_wrap


def _text_measure(node):
    def measure(_node, width, width_mode, height, height_mode):
        text = _text_content(node)
        natural_lines, natural_width = _text_lines(node, None, None)
        natural_height = len(natural_lines)

        width_value = None
        if width_mode != yoga.YGMeasureMode.YGMeasureModeUndefined and not math.isnan(width):
            width_value = width

        if width_value is None or natural_width <= width_value:
            return float(natural_width), float(natural_height)

        # Match Ink's special case when Yoga asks whether text can fit in <1px.
        if natural_width >= 1 and width_value > 0 and width_value < 1:
            return float(natural_width), float(natural_height)

        text_wrap = _node_style(node).get("textWrap", "wrap")
        width_limit = max(int(math.floor(width_value)), 0)
        if text_wrap == "wrap":
            wrapped_lines, measured_width = _text_lines(node, width_limit, None)
            measured_height = len(wrapped_lines)
        else:
            wrapped_text = text
            if width_limit > 0:
                wrapped_text = _wrap_text_value(text, width_limit, text_wrap)
            wrapped_lines = wrapped_text.split("\n") if wrapped_text else [""]
            measured_width = max((string_width(line) for line in wrapped_lines), default=0)
            measured_height = len(wrapped_lines)
        return float(measured_width), float(measured_height)

    return measure


def _set_length(node: Node, setter: str, value: Any) -> None:
    numeric = _numeric(value)
    if numeric is not None:
        getattr(node, setter)(numeric)
        return
    percent = _percent(value)
    if percent is not None and hasattr(node, f"{setter}_percent"):
        getattr(node, f"{setter}_percent")(percent)


def _apply_yoga_style(layout_node: Node, node) -> None:
    style = _node_style(node)
    node_name = getattr(node, "nodeName", None)

    if node_name in {"ink-root", "ink-fragment"}:
        layout_node.set_flex_direction(FLEX_DIRECTION_COLUMN)
        layout_node.set_align_items(ALIGN_STRETCH)
    elif node_name == "ink-box":
        layout_node.set_flex_direction(
            FLEX_DIRECTION_COLUMN if style.get("flexDirection", "column") == "column" else FLEX_DIRECTION_ROW
        )
        layout_node.set_align_items(
            {
                "center": ALIGN_CENTER,
                "flex-end": ALIGN_FLEX_END,
                "stretch": ALIGN_STRETCH,
            }.get(str(style.get("alignItems", "")) if style.get("alignItems") is not None else "", ALIGN_STRETCH)
        )
        layout_node.set_justify_content(
            {
                "center": JUSTIFY_CENTER,
                "flex-end": JUSTIFY_FLEX_END,
                "space-around": JUSTIFY_SPACE_AROUND,
                "space-between": JUSTIFY_SPACE_BETWEEN,
                "space-evenly": JUSTIFY_SPACE_EVENLY,
            }.get(
                str(style.get("justifyContent", "")) if style.get("justifyContent") is not None else "", JUSTIFY_FLEX_START
            )
        )
        layout_node.set_flex_wrap(WRAP_WRAP if style.get("flexWrap") == "wrap" else WRAP_NO_WRAP)
    else:
        layout_node.set_align_items(ALIGN_STRETCH)

    align_self = style.get("alignSelf")
    if align_self is not None:
        layout_node.set_align_self(
            {
                "auto": ALIGN_AUTO,
                "center": ALIGN_CENTER,
                "flex-start": ALIGN_FLEX_START,
                "flex-end": ALIGN_FLEX_END,
                "stretch": ALIGN_STRETCH,
            }.get(str(align_self) if isinstance(align_self, str) else "", ALIGN_AUTO)
        )

    _set_length(layout_node, "set_width", style.get("width", getattr(node, "width", None)))
    _set_length(layout_node, "set_height", style.get("height", getattr(node, "height", None)))
    _set_length(layout_node, "set_min_width", style.get("minWidth"))
    _set_length(layout_node, "set_max_width", style.get("maxWidth"))

    for edge, value in _edge_values(style, "padding").items():
        if value:
            layout_node.set_padding(edge, value)
    for edge, value in _edge_values(style, "margin").items():
        if value:
            layout_node.set_margin(edge, value)

    if style.get("borderStyle"):
        layout_node.set_border(EDGE_ALL, 1)
    if style.get("gap"):
        layout_node.set_gap(GUTTER_ALL, _int_value(style["gap"]))
    if "flexGrow" in style:
        layout_node.set_flex_grow(float(style["flexGrow"]))
    if "flexShrink" in style:
        layout_node.set_flex_shrink(float(style["flexShrink"]))


def _build_layout_tree(node):
    node_name = getattr(node, "nodeName", None)
    if node_name in {"#text", "ink-virtual-text"}:
        return None

    style_signature = (node_name, repr(sorted(_node_style(node).items())))
    layout_node = getattr(node, "_layout_node", None)
    if layout_node is None or getattr(node, "_layout_signature", None) != style_signature:
        previous_layout = layout_node
        previous_children = list(getattr(node, "_layout_children", []))
        if previous_layout is not None:
            for child_layout in previous_children:
                with contextlib.suppress(Exception):  # noqa: BLE001
                    previous_layout.remove_child(child_layout)
        layout_node = Node.create()
        node._layout_node = layout_node
        node._layout_signature = style_signature
        node._layout_children = []

    _apply_yoga_style(layout_node, node)

    if node_name == "ink-text":
        text_content = _text_content(node)
        measure_signature = _text_measure_signature(node, text_content)
        previous_signature = getattr(node, "_layout_measure_signature", None)
        if previous_signature is not None and previous_signature != measure_signature:
            with contextlib.suppress(Exception):  # noqa: BLE001
                layout_node.mark_dirty()
        node._layout_measure_signature = measure_signature
        layout_node._node.setMeasureFunc(_text_measure(node))
        node._layout_children = []
        return layout_node

    new_children = []
    for child in getattr(node, "childNodes", []):
        child_layout = _build_layout_tree(child)
        if child_layout is None:
            continue
        new_children.append(child_layout)

    existing_children = getattr(node, "_layout_children", [])
    if existing_children != new_children:
        for child_layout in existing_children:
            with contextlib.suppress(Exception):  # noqa: BLE001
                layout_node.remove_child(child_layout)
        for child_index, child_layout in enumerate(new_children):
            layout_node.insert_child(child_layout, child_index)
        node._layout_children = new_children
    return layout_node


def _layout_int(value: float | int | None) -> int:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return 0
    return max(int(round(value)), 0)


def _store_layout(node) -> None:
    layout_node = getattr(node, "_layout_node", None)
    if layout_node is not None:
        node.computed_width = _layout_int(layout_node.get_computed_width())
        node.computed_height = _layout_int(layout_node.get_computed_height())
        node.computed_left = _layout_int(layout_node.get_computed_left())
        node.computed_top = _layout_int(layout_node.get_computed_top())
    for child in getattr(node, "childNodes", []):
        _store_layout(child)


def compute_layout(node) -> None:
    layout_root = _build_layout_tree(node)
    if layout_root is None:
        return
    width = _numeric(getattr(node, "width", None))
    height = _numeric(getattr(node, "height", None))
    layout_root.calculate_layout(width, height, DIRECTION_LTR)
    _store_layout(node)


def _render_border(
    output: Output,
    width: int,
    height: int,
    style_name: str,
    border_color: str | None,
    *,
    x: int = 0,
    y: int = 0,
) -> None:
    if width < 2 or height < 2:
        return
    style = get_box_style(style_name)
    prefix = ANSI_OPEN.get(border_color, "") if border_color is not None else ""
    suffix = "\x1b[39m" if prefix else ""
    output.write(
        x,
        y,
        prefix + style.top_left + (style.top * max(width - 2, 0)) + style.top_right + suffix,
        {"transformers": [], "sanitized": True},
    )
    output.write(
        x,
        y + height - 1,
        prefix + style.bottom_left + (style.bottom * max(width - 2, 0)) + style.bottom_right + suffix,
        {"transformers": [], "sanitized": True},
    )
    for row in range(1, height - 1):
        output.write(x, y + row, prefix + style.left + suffix, {"transformers": [], "sanitized": True})
        output.write(x + width - 1, y + row, prefix + style.right + suffix, {"transformers": [], "sanitized": True})


def _render_background(output: Output, x: int, y: int, width: int, height: int, style: dict[str, Any]) -> None:
    background_sequence = _background_sequence(style.get("backgroundColor"))
    if background_sequence is None:
        return

    show_left = not (style.get("borderStyle") and style.get("borderLeft") is False)
    show_right = not (style.get("borderStyle") and style.get("borderRight") is False)
    show_top = not (style.get("borderStyle") and style.get("borderTop") is False)
    show_bottom = not (style.get("borderStyle") and style.get("borderBottom") is False)

    left_border = 1 if style.get("borderStyle") and show_left else 0
    right_border = 1 if style.get("borderStyle") and show_right else 0
    top_border = 1 if style.get("borderStyle") and show_top else 0
    bottom_border = 1 if style.get("borderStyle") and show_bottom else 0

    content_width = max(width - left_border - right_border, 0)
    content_height = max(height - top_border - bottom_border, 0)
    if content_width == 0 or content_height == 0:
        return

    fill = background_sequence + (" " * content_width) + "\x1b[49m"
    for row in range(content_height):
        output.write(x + left_border, y + top_border + row, fill, {"transformers": [], "sanitized": True})


def _get_max_width(node) -> int:
    layout_node = getattr(node, "_layout_node", None)
    if layout_node is None:
        return max(int(getattr(node, "computed_width", 0) or 0), 0)
    return max(
        _layout_int(layout_node.get_computed_width())
        - _layout_int(layout_node.get_computed_padding(EDGE_LEFT))
        - _layout_int(layout_node.get_computed_padding(EDGE_RIGHT))
        - _layout_int(layout_node.get_computed_border(EDGE_LEFT))
        - _layout_int(layout_node.get_computed_border(EDGE_RIGHT)),
        0,
    )


def _apply_padding_to_text(node, text: str) -> str:
    child_layout = getattr(getattr(node, "childNodes", [None])[0], "_layout_node", None)
    if child_layout is None:
        return text

    offset_x = _layout_int(child_layout.get_computed_left())
    offset_y = _layout_int(child_layout.get_computed_top())
    if offset_x <= 0 and offset_y <= 0:
        return text

    prefix = "\n" * offset_y
    indent = (" " * offset_x)
    return prefix + "\n".join(indent + line for line in text.splitlines())


def _background_transform(name: str | None):
    sequence = _background_sequence(name)
    if sequence is None:
        return None

    def apply(line: str, _index: int) -> str:
        return sequence + line + "\x1b[49m"

    return apply


def _render_text_to_canvas(node, output: Output, x: int, y: int, inherited_background: str | None, transformers: tuple = ()) -> None:
    text = squashTextNodes(node)
    if not text:
        return

    current_width = max((string_width(line) for line in text.split("\n")), default=0)
    max_width = _get_max_width(node)
    text_wrap = _node_style(node).get("textWrap", "wrap")
    if max_width > 0 and current_width > max_width:
        if text_wrap == "wrap":
            text_lines, _ = _text_lines(node, max_width, None)
            text = "\n".join(text_lines)
        else:
            text = _wrap_text_value(text, max_width, text_wrap)

    text = _apply_padding_to_text(node, text)
    active_transformers = list(transformers)
    style = _node_style(node)
    if inherited_background and not style.get("backgroundColor"):
        background_transform = _background_transform(inherited_background)
        if background_transform is not None:
            active_transformers = [background_transform, *active_transformers]

    output.write(x, y, text, {"transformers": active_transformers})


def _as_output_transform(transform):
    def apply(line: str, index: int):
        try:
            return transform(line, index)
        except TypeError:
            return transform(line)

    return apply


def _render_node_to_canvas(
    node,
    output: Output,
    *,
    offset_x: int = 0,
    offset_y: int = 0,
    inherited_background: str | None = None,
    transformers: tuple = (),
) -> None:
    node_name = getattr(node, "nodeName", None)
    if node_name == "#text":
        return

    style = _node_style(node)
    background_name = style.get("backgroundColor") or inherited_background
    x = offset_x + max(int(getattr(node, "computed_left", 0) or 0), 0)
    y = offset_y + max(int(getattr(node, "computed_top", 0) or 0), 0)
    width = max(int(getattr(node, "computed_width", 0) or 0), 0)
    height = max(int(getattr(node, "computed_height", 0) or 0), 0)

    next_transformers = transformers
    transform = getattr(node, "internal_transform", None)
    if transform is None:
        transform = getattr(node, "attributes", {}).get("internal_transform")
    if callable(transform):
        next_transformers = (_as_output_transform(transform), *transformers)

    if node_name == "ink-text":
        _render_text_to_canvas(node, output, x, y, background_name, next_transformers)
        return

    if width == 0 or height == 0:
        return

    if node_name == "ink-box":
        _render_background(output, x, y, width, height, style)
        if style.get("borderStyle"):
            _render_border(output, width, height, style["borderStyle"], style.get("borderColor"), x=x, y=y)

        clip_horizontally = style.get("overflowX") == "hidden" or style.get("overflow") == "hidden"
        clip_vertically = style.get("overflowY") == "hidden" or style.get("overflow") == "hidden"
        clipped = clip_horizontally or clip_vertically
        if clipped:
            border_left = 1 if style.get("borderStyle") and style.get("borderLeft", True) is not False else 0
            border_right = 1 if style.get("borderStyle") and style.get("borderRight", True) is not False else 0
            border_top = 1 if style.get("borderStyle") and style.get("borderTop", True) is not False else 0
            border_bottom = 1 if style.get("borderStyle") and style.get("borderBottom", True) is not False else 0
            output.clip(
                {
                    "x1": x + border_left if clip_horizontally else None,
                    "x2": x + width - border_right if clip_horizontally else None,
                    "y1": y + border_top if clip_vertically else None,
                    "y2": y + height - border_bottom if clip_vertically else None,
                }
            )

        visible_children = [
            child for child in getattr(node, "childNodes", []) if getattr(child, "nodeName", None) != "#text"
        ]
        if (
            style.get("borderStyle")
            and style.get("width")
            and
            style.get("flexDirection", "row") != "column"
            and len(visible_children) > 1
            and all(getattr(child, "nodeName", None) == "ink-text" for child in visible_children)
        ):
            pieces = []
            for index, child in enumerate(visible_children):
                piece = _inline_text(child)
                if index < len(visible_children) - 1:
                    piece = piece.rstrip(": ")
                pieces.append(piece)
            start_x = int(getattr(visible_children[0], "computed_left", 0) or 0)
            start_y = int(getattr(visible_children[0], "computed_top", 0) or 0)
            available_width = max(width - start_x - (1 if style.get("borderStyle") else 0), 1)
            combined = "".join(pieces)
            current_width = max((string_width(line) for line in combined.split("\n")), default=0)
            if current_width > available_width:
                combined = _wrap_text_value(combined, available_width, "wrap")
            output.write(start_x, start_y, combined, {"transformers": next_transformers})
            if clipped:
                output.unclip()
            return

        for child in getattr(node, "childNodes", []):
            _render_node_to_canvas(
                child,
                output,
                offset_x=x,
                offset_y=y,
                inherited_background=background_name,
                transformers=next_transformers,
            )

        if clipped:
            output.unclip()
        return

    for child in getattr(node, "childNodes", []):
        _render_node_to_canvas(
            child,
            output,
            offset_x=x,
            offset_y=y,
            inherited_background=background_name,
            transformers=next_transformers,
        )


def _render_natural_box(
    node,
    style: dict[str, Any],
    effective_background: str | None,
    *,
    width_hint: int = 0,
    height_hint: int = 0,
) -> RenderedBlock:
    visible_children = [
        child
        for child in getattr(node, "childNodes", [])
        if getattr(child, "nodeName", None) != "#text"
    ]
    child_blocks = [_render_block(child, effective_background) for child in visible_children]
    gap = _int_value(style.get("gap", 0))
    direction = style.get("flexDirection", "column")
    padding = _edge_values(style, "padding")
    border_size = 1 if style.get("borderStyle") else 0
    background_sequence = _background_sequence(effective_background)

    if direction == "row":
        content_width = sum(block.width for block in child_blocks) + max(len(child_blocks) - 1, 0) * gap
        content_height = max((block.height for block in child_blocks), default=0)
    else:
        content_width = max((block.width for block in child_blocks), default=0)
        content_height = sum(block.height for block in child_blocks) + max(len(child_blocks) - 1, 0) * gap

    width = width_hint or max(
        _int_value(style.get("width", 0)),
        content_width + padding[EDGE_LEFT] + padding[EDGE_RIGHT] + border_size * 2,
    )
    height = height_hint or max(
        _int_value(style.get("height", 0)),
        content_height + padding[EDGE_TOP] + padding[EDGE_BOTTOM] + border_size * 2,
    )

    if width == 0 or height == 0:
        return RenderedBlock([], width, height)

    output = Output({"width": width, "height": height})
    inner_width = max(width - border_size * 2, 0)
    inner_height = max(height - border_size * 2, 0)
    if background_sequence and inner_width > 0 and inner_height > 0:
        fill = background_sequence + (" " * inner_width) + "\x1b[49m"
        for y in range(border_size, border_size + inner_height):
            output.write(border_size, y, fill, {"transformers": []})

    cursor_x = border_size + padding[EDGE_LEFT]
    cursor_y = border_size + padding[EDGE_TOP]
    for _index, block in enumerate(child_blocks):
        for line_index, line in enumerate(block.lines):
            output.write(cursor_x, cursor_y + line_index, line, {"transformers": []})
        if direction == "row":
            cursor_x += block.width + gap
        else:
            cursor_y += block.height + gap

    if style.get("borderStyle"):
        _render_border(output, width, height, style["borderStyle"], style.get("borderColor"))

    lines = output.get().output.splitlines()
    if not lines and height > 0:
        lines = ["" for _ in range(height)]
    return RenderedBlock(lines, width, max(height, len(lines)))


def _render_block(node, inherited_background: str | None) -> RenderedBlock:
    node_name = getattr(node, "nodeName", None)
    if node_name == "#text":
        text = getattr(node, "nodeValue", "")
        return RenderedBlock([text], string_width(text), 1)

    style = _node_style(node)
    background_name = style.get("backgroundColor")
    effective_background = background_name or inherited_background
    width = max(int(getattr(node, "computed_width", 0) or 0), 0)
    height = max(int(getattr(node, "computed_height", 0) or 0), 0)

    if node_name == "ink-text":
        width_limit = width if width > 0 else None
        lines, measured_width = _text_lines(node, width_limit, _background_sequence(effective_background))
        block_height = max(height, len(lines))
        if block_height > len(lines):
            lines = lines + [""] * (block_height - len(lines))
        return RenderedBlock(lines, width or measured_width, block_height)

    if width == 0 or height == 0:
        return _render_natural_box(node, style, effective_background, width_hint=width, height_hint=height)

    output = Output({"width": width, "height": height})
    border_size = 1 if style.get("borderStyle") else 0
    inner_width = max(width - border_size * 2, 0)
    inner_height = max(height - border_size * 2, 0)
    background_sequence = _background_sequence(effective_background)
    if background_sequence and inner_width > 0 and inner_height > 0:
        fill = background_sequence + (" " * inner_width) + "\x1b[49m"
        for y in range(border_size, border_size + inner_height):
            output.write(border_size, y, fill, {"transformers": []})

    visible_children = [
        child
        for child in getattr(node, "childNodes", [])
        if getattr(child, "nodeName", None) != "#text"
    ]
    if visible_children and any(int(getattr(child, "computed_height", 0) or 0) == 0 for child in visible_children):
        return _render_natural_box(
            node,
            style,
            effective_background,
            width_hint=width,
            height_hint=0,
        )
    if (
        node_name == "ink-box"
        and style.get("borderStyle")
        and style.get("width")
        and style.get("flexDirection", "row") != "column"
        and len(visible_children) > 1
        and all(getattr(child, "nodeName", None) == "ink-text" for child in visible_children)
    ):
        pieces = [_inline_text(child) for child in visible_children]
        combined = "".join(piece.rstrip(": ") if index < len(pieces) - 1 else piece for index, piece in enumerate(pieces))
        start_x = int(getattr(visible_children[0], "computed_left", border_size) or border_size)
        start_y = int(getattr(visible_children[0], "computed_top", border_size) or border_size)
        available_width = max(width - start_x - border_size, 1)
        synthetic_cells = Output._styled_cells(combined)
        synthetic_cells = _apply_background(synthetic_cells, _background_sequence(effective_background))
        synthetic_lines = [Output._styled_cells_to_string(line) for line in _wrap_cells(synthetic_cells, available_width)]
        for line_index, line in enumerate(synthetic_lines):
            output.write(start_x, start_y + line_index, line, {"transformers": []})
        if style.get("borderStyle"):
            _render_border(output, width, height, style["borderStyle"], style.get("borderColor"))
        lines = output.get().output.splitlines()
        if not lines and height > 0:
            lines = ["" for _ in range(height)]
        return RenderedBlock(lines, width, max(height, len(lines)))

    for child in getattr(node, "childNodes", []):
        if getattr(child, "nodeName", None) == "#text" and node_name != "ink-text":
            continue
        child_block = _render_block(child, effective_background)
        child_left = int(getattr(child, "computed_left", 0) or 0)
        child_top = int(getattr(child, "computed_top", 0) or 0)
        for line_index, line in enumerate(child_block.lines):
            output.write(child_left, child_top + line_index, line, {"transformers": []})

    if style.get("borderStyle"):
        _render_border(output, width, height, style["borderStyle"], style.get("borderColor"))

    lines = output.get().output.splitlines()
    if not lines and height > 0:
        lines = ["" for _ in range(height)]
    return RenderedBlock(lines, width, max(height, len(lines)))


def render_node_output(node) -> str:
    if not hasattr(node, "computed_width") and getattr(node, "nodeName", None) != "#text":
        compute_layout(node)
    width = max(int(getattr(node, "computed_width", 0) or 0), 0)
    height = max(int(getattr(node, "computed_height", 0) or 0), 0)
    if width == 0 or height == 0:
        return ""
    output = Output({"width": width, "height": height})
    _render_node_to_canvas(node, output)
    return output.get().output


__all__ = ["compute_layout", "render_node_output"]
