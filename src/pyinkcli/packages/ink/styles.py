"""
Styles for pyinkcli components.

Maps CSS-like style properties to Yoga layout engine values.
"""

from __future__ import annotations

from typing import Literal, TypedDict

from pyinkcli import _yoga as yoga

# Text wrap options
TextWrap = Literal[
    "wrap",
    "end",
    "middle",
    "truncate-end",
    "truncate",
    "truncate-middle",
    "truncate-start",
]

# Position options
Position = Literal["absolute", "relative", "static"]

# Flex direction options
FlexDirection = Literal["row", "column", "row-reverse", "column-reverse"]

# Flex wrap options
FlexWrap = Literal["nowrap", "wrap", "wrap-reverse"]

# Align items options
AlignItems = Literal["flex-start", "center", "flex-end", "stretch", "baseline"]

# Align self options
AlignSelf = Literal["flex-start", "center", "flex-end", "auto", "stretch", "baseline"]

# Align content options
AlignContent = Literal[
    "flex-start",
    "flex-end",
    "center",
    "stretch",
    "space-between",
    "space-around",
    "space-evenly",
]

# Justify content options
JustifyContent = Literal[
    "flex-start",
    "flex-end",
    "space-between",
    "space-around",
    "space-evenly",
    "center",
]

# Display options
Display = Literal["flex", "none"]

# Overflow options
Overflow = Literal["visible", "hidden"]

# Box style names
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


class Styles(TypedDict, total=False):
    """Style properties for Box components."""

    # Text
    textWrap: TextWrap

    # Position
    position: Position
    top: int | str
    right: int | str
    bottom: int | str
    left: int | str

    # Gap
    columnGap: int
    rowGap: int
    gap: int

    # Margin
    margin: int
    marginX: int
    marginY: int
    marginTop: int
    marginBottom: int
    marginLeft: int
    marginRight: int

    # Padding
    padding: int
    paddingX: int
    paddingY: int
    paddingTop: int
    paddingBottom: int
    paddingLeft: int
    paddingRight: int

    # Flex
    flexGrow: float
    flexShrink: float
    flexDirection: FlexDirection
    flexBasis: int | str
    flexWrap: FlexWrap
    alignItems: AlignItems
    alignSelf: AlignSelf
    alignContent: AlignContent
    justifyContent: JustifyContent

    # Dimensions
    width: int | str
    height: int | str
    minWidth: int | str
    minHeight: int | str
    maxWidth: int | str
    maxHeight: int | str
    aspectRatio: float

    # Display
    display: Display

    # Border
    borderStyle: BoxStyleName | None
    borderTop: bool
    borderBottom: bool
    borderLeft: bool
    borderRight: bool
    borderColor: str
    borderTopColor: str
    borderBottomColor: str
    borderLeftColor: str
    borderRightColor: str
    borderDimColor: bool
    borderTopDimColor: bool
    borderBottomDimColor: bool
    borderLeftDimColor: bool
    borderRightDimColor: bool

    # Overflow
    overflow: Overflow
    overflowX: Overflow
    overflowY: Overflow

    # Background
    backgroundColor: str


def apply_styles(
    yoga_node: yoga.Node,
    style: Styles,
    current_style: Styles | None = None,
) -> None:
    """
    Apply style properties to a Yoga node.

    Args:
        yoga_node: The Yoga node to style.
        style: The new/changed style properties.
        current_style: The current complete style (for border calculations).
    """
    if current_style is None:
        current_style = style

    _apply_position_styles(yoga_node, style)
    _apply_margin_styles(yoga_node, style)
    _apply_padding_styles(yoga_node, style)
    _apply_flex_styles(yoga_node, style)
    _apply_dimension_styles(yoga_node, style)
    _apply_display_styles(yoga_node, style)
    _apply_border_styles(yoga_node, style, current_style)
    _apply_gap_styles(yoga_node, style)


def _apply_position_styles(yoga_node: yoga.Node, style: Styles) -> None:
    """Apply position-related styles."""
    if "position" in style:
        position = style["position"]
        if position == "absolute":
            yoga_node.set_position_type(yoga.POSITION_TYPE_ABSOLUTE)
        elif position == "static":
            yoga_node.set_position_type(yoga.POSITION_TYPE_STATIC)
        else:
            yoga_node.set_position_type(yoga.POSITION_TYPE_RELATIVE)

    position_edges = [
        ("top", yoga.EDGE_TOP),
        ("right", yoga.EDGE_RIGHT),
        ("bottom", yoga.EDGE_BOTTOM),
        ("left", yoga.EDGE_LEFT),
    ]

    for prop, edge in position_edges:
        if prop not in style:
            continue
        value = style[prop]
        if isinstance(value, str):
            yoga_node.set_position_percent(edge, float(value.rstrip("%")))
        else:
            yoga_node.set_position(edge, value)


def _apply_margin_styles(yoga_node: yoga.Node, style: Styles) -> None:
    """Apply margin-related styles."""
    if "margin" in style:
        yoga_node.set_margin(yoga.EDGE_ALL, style["margin"])

    if "marginX" in style:
        yoga_node.set_margin(yoga.EDGE_HORIZONTAL, style["marginX"])

    if "marginY" in style:
        yoga_node.set_margin(yoga.EDGE_VERTICAL, style["marginY"])

    if "marginLeft" in style:
        yoga_node.set_margin(yoga.EDGE_START, style["marginLeft"] or 0)

    if "marginRight" in style:
        yoga_node.set_margin(yoga.EDGE_END, style["marginRight"] or 0)

    if "marginTop" in style:
        yoga_node.set_margin(yoga.EDGE_TOP, style["marginTop"] or 0)

    if "marginBottom" in style:
        yoga_node.set_margin(yoga.EDGE_BOTTOM, style["marginBottom"] or 0)


def _apply_padding_styles(yoga_node: yoga.Node, style: Styles) -> None:
    """Apply padding-related styles."""
    if "padding" in style:
        yoga_node.set_padding(yoga.EDGE_ALL, style["padding"])

    if "paddingX" in style:
        yoga_node.set_padding(yoga.EDGE_HORIZONTAL, style["paddingX"])

    if "paddingY" in style:
        yoga_node.set_padding(yoga.EDGE_VERTICAL, style["paddingY"])

    if "paddingLeft" in style:
        yoga_node.set_padding(yoga.EDGE_LEFT, style["paddingLeft"] or 0)

    if "paddingRight" in style:
        yoga_node.set_padding(yoga.EDGE_RIGHT, style["paddingRight"] or 0)

    if "paddingTop" in style:
        yoga_node.set_padding(yoga.EDGE_TOP, style["paddingTop"] or 0)

    if "paddingBottom" in style:
        yoga_node.set_padding(yoga.EDGE_BOTTOM, style["paddingBottom"] or 0)


def _apply_flex_styles(yoga_node: yoga.Node, style: Styles) -> None:
    """Apply flex-related styles."""
    if "flexGrow" in style:
        yoga_node.set_flex_grow(style["flexGrow"])

    if "flexShrink" in style:
        shrink = style["flexShrink"]
        yoga_node.set_flex_shrink(shrink if isinstance(shrink, (int, float)) else 1)

    if "flexWrap" in style:
        wrap = style["flexWrap"]
        if wrap == "nowrap":
            yoga_node.set_flex_wrap(yoga.WRAP_NO_WRAP)
        elif wrap == "wrap":
            yoga_node.set_flex_wrap(yoga.WRAP_WRAP)
        elif wrap == "wrap-reverse":
            yoga_node.set_flex_wrap(yoga.WRAP_WRAP_REVERSE)

    if "flexDirection" in style:
        direction = style["flexDirection"]
        if direction == "row":
            yoga_node.set_flex_direction(yoga.FLEX_DIRECTION_ROW)
        elif direction == "row-reverse":
            yoga_node.set_flex_direction(yoga.FLEX_DIRECTION_ROW_REVERSE)
        elif direction == "column":
            yoga_node.set_flex_direction(yoga.FLEX_DIRECTION_COLUMN)
        elif direction == "column-reverse":
            yoga_node.set_flex_direction(yoga.FLEX_DIRECTION_COLUMN_REVERSE)

    if "flexBasis" in style:
        basis = style["flexBasis"]
        if isinstance(basis, int):
            yoga_node.set_flex_basis(float(basis))
        elif isinstance(basis, str):
            yoga_node.set_flex_basis_percent(float(basis.rstrip("%")))
        else:
            yoga_node.set_flex_basis(float("nan"))

    if "alignItems" in style:
        align = style["alignItems"]
        if align == "stretch" or not align:
            yoga_node.set_align_items(yoga.ALIGN_STRETCH)
        elif align == "flex-start":
            yoga_node.set_align_items(yoga.ALIGN_FLEX_START)
        elif align == "center":
            yoga_node.set_align_items(yoga.ALIGN_CENTER)
        elif align == "flex-end":
            yoga_node.set_align_items(yoga.ALIGN_FLEX_END)
        elif align == "baseline":
            yoga_node.set_align_items(yoga.ALIGN_BASELINE)

    if "alignSelf" in style:
        align = style["alignSelf"]
        if align == "auto" or not align:
            yoga_node.set_align_self(yoga.ALIGN_AUTO)
        elif align == "flex-start":
            yoga_node.set_align_self(yoga.ALIGN_FLEX_START)
        elif align == "center":
            yoga_node.set_align_self(yoga.ALIGN_CENTER)
        elif align == "flex-end":
            yoga_node.set_align_self(yoga.ALIGN_FLEX_END)
        elif align == "stretch":
            yoga_node.set_align_self(yoga.ALIGN_STRETCH)
        elif align == "baseline":
            yoga_node.set_align_self(yoga.ALIGN_BASELINE)

    if "alignContent" in style:
        align = style["alignContent"]
        if align == "flex-start" or not align:
            yoga_node.set_align_content(yoga.ALIGN_FLEX_START)
        elif align == "center":
            yoga_node.set_align_content(yoga.ALIGN_CENTER)
        elif align == "flex-end":
            yoga_node.set_align_content(yoga.ALIGN_FLEX_END)
        elif align == "stretch":
            yoga_node.set_align_content(yoga.ALIGN_STRETCH)
        elif align == "space-between":
            yoga_node.set_align_content(yoga.ALIGN_SPACE_BETWEEN)
        elif align == "space-around":
            yoga_node.set_align_content(yoga.ALIGN_SPACE_AROUND)
        elif align == "space-evenly":
            yoga_node.set_align_content(yoga.ALIGN_SPACE_EVENLY)

    if "justifyContent" in style:
        justify = style["justifyContent"]
        if justify == "flex-start" or not justify:
            yoga_node.set_justify_content(yoga.JUSTIFY_FLEX_START)
        elif justify == "center":
            yoga_node.set_justify_content(yoga.JUSTIFY_CENTER)
        elif justify == "flex-end":
            yoga_node.set_justify_content(yoga.JUSTIFY_FLEX_END)
        elif justify == "space-between":
            yoga_node.set_justify_content(yoga.JUSTIFY_SPACE_BETWEEN)
        elif justify == "space-around":
            yoga_node.set_justify_content(yoga.JUSTIFY_SPACE_AROUND)
        elif justify == "space-evenly":
            yoga_node.set_justify_content(yoga.JUSTIFY_SPACE_EVENLY)


def _apply_dimension_styles(yoga_node: yoga.Node, style: Styles) -> None:
    """Apply dimension-related styles."""
    if "width" in style:
        width = style["width"]
        if isinstance(width, int):
            yoga_node.set_width(float(width))
        elif isinstance(width, str):
            yoga_node.set_width_percent(float(width.rstrip("%")))
        else:
            yoga_node.set_width_auto()

    if "height" in style:
        height = style["height"]
        if isinstance(height, int):
            yoga_node.set_height(float(height))
        elif isinstance(height, str):
            yoga_node.set_height_percent(float(height.rstrip("%")))
        else:
            yoga_node.set_height_auto()

    if "minWidth" in style:
        min_width = style["minWidth"]
        if isinstance(min_width, str):
            yoga_node.set_min_width_percent(float(min_width.rstrip("%")))
        else:
            yoga_node.set_min_width(float(min_width or 0))

    if "minHeight" in style:
        min_height = style["minHeight"]
        if isinstance(min_height, str):
            yoga_node.set_min_height_percent(float(min_height.rstrip("%")))
        else:
            yoga_node.set_min_height(float(min_height or 0))

    if "maxWidth" in style:
        max_width = style["maxWidth"]
        if isinstance(max_width, str):
            yoga_node.set_max_width_percent(float(max_width.rstrip("%")))
        else:
            yoga_node.set_max_width(float(max_width))

    if "maxHeight" in style:
        max_height = style["maxHeight"]
        if isinstance(max_height, str):
            yoga_node.set_max_height_percent(float(max_height.rstrip("%")))
        else:
            yoga_node.set_max_height(float(max_height))

    if "aspectRatio" in style:
        yoga_node.set_aspect_ratio(float(style["aspectRatio"]))


def _apply_display_styles(yoga_node: yoga.Node, style: Styles) -> None:
    """Apply display-related styles."""
    if "display" in style:
        display = style["display"]
        yoga_node.set_display(
            yoga.DISPLAY_FLEX if display == "flex" else yoga.DISPLAY_NONE
        )


def _apply_border_styles(
    yoga_node: yoga.Node,
    style: Styles,
    current_style: Styles,
) -> None:
    """Apply border-related styles."""
    has_border_changes = any(
        key in style
        for key in [
            "borderStyle",
            "borderTop",
            "borderBottom",
            "borderLeft",
            "borderRight",
        ]
    )

    if not has_border_changes:
        return

    border_width = 1 if current_style.get("borderStyle") else 0

    yoga_node.set_border(
        yoga.EDGE_TOP, 0 if current_style.get("borderTop") is False else border_width
    )
    yoga_node.set_border(
        yoga.EDGE_BOTTOM, 0 if current_style.get("borderBottom") is False else border_width
    )
    yoga_node.set_border(
        yoga.EDGE_LEFT, 0 if current_style.get("borderLeft") is False else border_width
    )
    yoga_node.set_border(
        yoga.EDGE_RIGHT, 0 if current_style.get("borderRight") is False else border_width
    )


def _apply_gap_styles(yoga_node: yoga.Node, style: Styles) -> None:
    """Apply gap-related styles."""
    if "gap" in style:
        yoga_node.set_gap(yoga.GUTTER_ALL, float(style["gap"]))

    if "columnGap" in style:
        yoga_node.set_gap(yoga.GUTTER_COLUMN, float(style["columnGap"]))

    if "rowGap" in style:
        yoga_node.set_gap(yoga.GUTTER_ROW, float(style["rowGap"]))


__all__ = ["Styles"]
