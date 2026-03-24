from __future__ import annotations

from dataclasses import dataclass

import yoga

UNDEFINED = float("nan")

YGDirection = yoga.YGDirection
DIRECTION_INHERIT = yoga.YGDirection.YGDirectionInherit
DIRECTION_LTR = yoga.YGDirection.YGDirectionLTR
DIRECTION_RTL = yoga.YGDirection.YGDirectionRTL

YGFlexDirection = yoga.YGFlexDirection
FLEX_DIRECTION_COLUMN = yoga.YGFlexDirection.YGFlexDirectionColumn
FLEX_DIRECTION_COLUMN_REVERSE = yoga.YGFlexDirection.YGFlexDirectionColumnReverse
FLEX_DIRECTION_ROW = yoga.YGFlexDirection.YGFlexDirectionRow
FLEX_DIRECTION_ROW_REVERSE = yoga.YGFlexDirection.YGFlexDirectionRowReverse

YGJustify = yoga.YGJustify
JUSTIFY_FLEX_START = yoga.YGJustify.YGJustifyFlexStart
JUSTIFY_CENTER = yoga.YGJustify.YGJustifyCenter
JUSTIFY_FLEX_END = yoga.YGJustify.YGJustifyFlexEnd
JUSTIFY_SPACE_BETWEEN = yoga.YGJustify.YGJustifySpaceBetween
JUSTIFY_SPACE_AROUND = yoga.YGJustify.YGJustifySpaceAround
JUSTIFY_SPACE_EVENLY = yoga.YGJustify.YGJustifySpaceEvenly

YGAlign = yoga.YGAlign
ALIGN_AUTO = yoga.YGAlign.YGAlignAuto
ALIGN_FLEX_START = yoga.YGAlign.YGAlignFlexStart
ALIGN_CENTER = yoga.YGAlign.YGAlignCenter
ALIGN_FLEX_END = yoga.YGAlign.YGAlignFlexEnd
ALIGN_STRETCH = yoga.YGAlign.YGAlignStretch
ALIGN_BASELINE = yoga.YGAlign.YGAlignBaseline
ALIGN_SPACE_BETWEEN = yoga.YGAlign.YGAlignSpaceBetween
ALIGN_SPACE_AROUND = yoga.YGAlign.YGAlignSpaceAround
ALIGN_SPACE_EVENLY = yoga.YGAlign.YGAlignSpaceEvenly

YGWrap = yoga.YGWrap
WRAP_NO_WRAP = yoga.YGWrap.YGWrapNoWrap
WRAP_WRAP = yoga.YGWrap.YGWrapWrap
WRAP_WRAP_REVERSE = yoga.YGWrap.YGWrapWrapReverse

YGPositionType = yoga.YGPositionType
POSITION_TYPE_STATIC = yoga.YGPositionType.YGPositionTypeStatic
POSITION_TYPE_RELATIVE = yoga.YGPositionType.YGPositionTypeRelative
POSITION_TYPE_ABSOLUTE = yoga.YGPositionType.YGPositionTypeAbsolute

YGDisplay = yoga.YGDisplay
DISPLAY_FLEX = yoga.YGDisplay.YGDisplayFlex
DISPLAY_NONE = yoga.YGDisplay.YGDisplayNone

YGEdge = yoga.YGEdge
EDGE_LEFT = yoga.YGEdge.YGEdgeLeft
EDGE_TOP = yoga.YGEdge.YGEdgeTop
EDGE_RIGHT = yoga.YGEdge.YGEdgeRight
EDGE_BOTTOM = yoga.YGEdge.YGEdgeBottom
EDGE_START = yoga.YGEdge.YGEdgeStart
EDGE_END = yoga.YGEdge.YGEdgeEnd
EDGE_HORIZONTAL = yoga.YGEdge.YGEdgeHorizontal
EDGE_VERTICAL = yoga.YGEdge.YGEdgeVertical
EDGE_ALL = yoga.YGEdge.YGEdgeAll

YGGutter = yoga.YGGutter
GUTTER_COLUMN = yoga.YGGutter.YGGutterColumn
GUTTER_ROW = yoga.YGGutter.YGGutterRow
GUTTER_ALL = yoga.YGGutter.YGGutterAll


class Config:
    @classmethod
    def create(cls) -> "Config":
        return cls()


@dataclass
class LayoutNode:
    left: float = 0
    top: float = 0
    width: float = 0
    height: float = 0


class Node:
    def __init__(self) -> None:
        self._node = yoga.Node()

    @classmethod
    def create(cls, config: Config | None = None) -> "Node":
        return cls()

    def insert_child(self, child: "Node", index: int) -> None:
        yoga.YGNodeInsertChild(self._node, child._node, index)

    def remove_child(self, child: "Node") -> None:
        yoga.YGNodeRemoveChild(self._node, child._node)

    def calculate_layout(
        self,
        width: float | None = None,
        height: float | None = None,
        direction= DIRECTION_LTR,
    ) -> None:
        yoga.YGNodeCalculateLayout(self._node, float("nan") if width is None else width, float("nan") if height is None else height, direction)

    def mark_dirty(self) -> None:
        yoga.YGNodeMarkDirty(self._node)

    def set_width(self, value: float) -> None:
        yoga.YGNodeStyleSetWidth(self._node, float(value))

    def set_width_percent(self, value: float) -> None:
        yoga.YGNodeStyleSetWidthPercent(self._node, float(value))

    def set_height(self, value: float) -> None:
        yoga.YGNodeStyleSetHeight(self._node, float(value))

    def set_height_percent(self, value: float) -> None:
        yoga.YGNodeStyleSetHeightPercent(self._node, float(value))

    def set_flex_direction(self, value) -> None:
        yoga.YGNodeStyleSetFlexDirection(self._node, value)

    def set_align_items(self, value) -> None:
        yoga.YGNodeStyleSetAlignItems(self._node, value)

    def set_align_self(self, value) -> None:
        yoga.YGNodeStyleSetAlignSelf(self._node, value)

    def set_justify_content(self, value) -> None:
        yoga.YGNodeStyleSetJustifyContent(self._node, value)

    def set_padding(self, edge, value: float) -> None:
        yoga.YGNodeStyleSetPadding(self._node, edge, float(value))

    def set_margin(self, edge, value: float) -> None:
        yoga.YGNodeStyleSetMargin(self._node, edge, float(value))

    def set_border(self, edge, value: float) -> None:
        yoga.YGNodeStyleSetBorder(self._node, edge, float(value))

    def set_flex_grow(self, value: float) -> None:
        yoga.YGNodeStyleSetFlexGrow(self._node, float(value))

    def set_flex_shrink(self, value: float) -> None:
        yoga.YGNodeStyleSetFlexShrink(self._node, float(value))

    def set_display(self, value) -> None:
        yoga.YGNodeStyleSetDisplay(self._node, value)

    def set_position_type(self, value) -> None:
        yoga.YGNodeStyleSetPositionType(self._node, value)

    def set_position(self, edge, value: float) -> None:
        yoga.YGNodeStyleSetPosition(self._node, edge, float(value))

    def set_flex_wrap(self, value) -> None:
        yoga.YGNodeStyleSetFlexWrap(self._node, value)

    def set_gap(self, gutter, value: float) -> None:
        yoga.YGNodeStyleSetGap(self._node, gutter, float(value))

    def set_min_width(self, value: float) -> None:
        yoga.YGNodeStyleSetMinWidth(self._node, float(value))

    def set_min_width_percent(self, value: float) -> None:
        yoga.YGNodeStyleSetMinWidthPercent(self._node, float(value))

    def set_max_width(self, value: float) -> None:
        yoga.YGNodeStyleSetMaxWidth(self._node, float(value))

    def set_max_width_percent(self, value: float) -> None:
        yoga.YGNodeStyleSetMaxWidthPercent(self._node, float(value))

    def get_computed_width(self) -> float:
        return float(yoga.YGNodeLayoutGetWidth(self._node))

    def get_computed_height(self) -> float:
        return float(yoga.YGNodeLayoutGetHeight(self._node))

    def get_computed_left(self) -> float:
        return float(yoga.YGNodeLayoutGetLeft(self._node))

    def get_computed_top(self) -> float:
        return float(yoga.YGNodeLayoutGetTop(self._node))

    def get_computed_padding(self, edge) -> float:
        return float(yoga.YGNodeLayoutGetPadding(self._node, edge))

    def get_computed_border(self, edge) -> float:
        return float(yoga.YGNodeLayoutGetBorder(self._node, edge))


__all__ = [
    "LayoutNode",
    "Node",
    "Config",
    "YGDirection",
    "DIRECTION_INHERIT",
    "DIRECTION_LTR",
    "DIRECTION_RTL",
    "YGFlexDirection",
    "FLEX_DIRECTION_COLUMN",
    "FLEX_DIRECTION_COLUMN_REVERSE",
    "FLEX_DIRECTION_ROW",
    "FLEX_DIRECTION_ROW_REVERSE",
    "YGJustify",
    "JUSTIFY_FLEX_START",
    "JUSTIFY_CENTER",
    "JUSTIFY_FLEX_END",
    "JUSTIFY_SPACE_BETWEEN",
    "JUSTIFY_SPACE_AROUND",
    "JUSTIFY_SPACE_EVENLY",
    "YGAlign",
    "ALIGN_AUTO",
    "ALIGN_FLEX_START",
    "ALIGN_CENTER",
    "ALIGN_FLEX_END",
    "ALIGN_STRETCH",
    "ALIGN_BASELINE",
    "ALIGN_SPACE_BETWEEN",
    "ALIGN_SPACE_AROUND",
    "ALIGN_SPACE_EVENLY",
    "YGWrap",
    "WRAP_NO_WRAP",
    "WRAP_WRAP",
    "WRAP_WRAP_REVERSE",
    "YGPositionType",
    "POSITION_TYPE_STATIC",
    "POSITION_TYPE_RELATIVE",
    "POSITION_TYPE_ABSOLUTE",
    "YGDisplay",
    "DISPLAY_FLEX",
    "DISPLAY_NONE",
    "YGEdge",
    "EDGE_LEFT",
    "EDGE_TOP",
    "EDGE_RIGHT",
    "EDGE_BOTTOM",
    "EDGE_START",
    "EDGE_END",
    "EDGE_HORIZONTAL",
    "EDGE_VERTICAL",
    "EDGE_ALL",
    "YGGutter",
    "GUTTER_COLUMN",
    "GUTTER_ROW",
    "GUTTER_ALL",
    "UNDEFINED",
]
