"""
Compatibility layer for yoga-layout-python.

Provides a consistent API matching the project's original yoga implementation.
"""

from __future__ import annotations

import importlib
import math
from collections.abc import Callable
from typing import TYPE_CHECKING

import yoga
from yoga import Config as YogaConfig
from yoga import Node as YogaNode

_yoga_style_module = importlib.import_module("yoga.style.Style")
if not hasattr(_yoga_style_module, "maxOrDefined") and hasattr(_yoga_style_module, "maxOrDefinedFloat"):
    _yoga_style_module.maxOrDefined = _yoga_style_module.maxOrDefinedFloat

if TYPE_CHECKING:
    pass


# Re-export enums from yoga-layout-python
class YGDirection:
    YGDirectionInherit = yoga.YGDirection.YGDirectionInherit
    YGDirectionLTR = yoga.YGDirection.YGDirectionLTR
    YGDirectionRTL = yoga.YGDirection.YGDirectionRTL


class YGFlexDirection:
    YGFlexDirectionColumn = yoga.YGFlexDirection.YGFlexDirectionColumn
    YGFlexDirectionColumnReverse = yoga.YGFlexDirection.YGFlexDirectionColumnReverse
    YGFlexDirectionRow = yoga.YGFlexDirection.YGFlexDirectionRow
    YGFlexDirectionRowReverse = yoga.YGFlexDirection.YGFlexDirectionRowReverse


class YGJustify:
    YGJustifyFlexStart = yoga.YGJustify.YGJustifyFlexStart
    YGJustifyCenter = yoga.YGJustify.YGJustifyCenter
    YGJustifyFlexEnd = yoga.YGJustify.YGJustifyFlexEnd
    YGJustifySpaceBetween = yoga.YGJustify.YGJustifySpaceBetween
    YGJustifySpaceAround = yoga.YGJustify.YGJustifySpaceAround
    YGJustifySpaceEvenly = yoga.YGJustify.YGJustifySpaceEvenly


class YGAlign:
    YGAlignAuto = yoga.YGAlign.YGAlignAuto
    YGAlignFlexStart = yoga.YGAlign.YGAlignFlexStart
    YGAlignCenter = yoga.YGAlign.YGAlignCenter
    YGAlignFlexEnd = yoga.YGAlign.YGAlignFlexEnd
    YGAlignStretch = yoga.YGAlign.YGAlignStretch
    YGAlignBaseline = yoga.YGAlign.YGAlignBaseline
    YGAlignSpaceBetween = yoga.YGAlign.YGAlignSpaceBetween
    YGAlignSpaceAround = yoga.YGAlign.YGAlignSpaceAround
    YGAlignSpaceEvenly = yoga.YGAlign.YGAlignSpaceEvenly


class YGWrap:
    YGWrapNoWrap = yoga.YGWrap.YGWrapNoWrap
    YGWrapWrap = yoga.YGWrap.YGWrapWrap
    YGWrapWrapReverse = yoga.YGWrap.YGWrapWrapReverse


class YGPositionType:
    YGPositionTypeStatic = yoga.YGPositionType.YGPositionTypeStatic
    YGPositionTypeRelative = yoga.YGPositionType.YGPositionTypeRelative
    YGPositionTypeAbsolute = yoga.YGPositionType.YGPositionTypeAbsolute


class YGDisplay:
    YGDisplayFlex = yoga.YGDisplay.YGDisplayFlex
    YGDisplayNone = yoga.YGDisplay.YGDisplayNone


class YGEdge:
    YGEdgeLeft = yoga.YGEdge.YGEdgeLeft
    YGEdgeTop = yoga.YGEdge.YGEdgeTop
    YGEdgeRight = yoga.YGEdge.YGEdgeRight
    YGEdgeBottom = yoga.YGEdge.YGEdgeBottom
    YGEdgeStart = yoga.YGEdge.YGEdgeStart
    YGEdgeEnd = yoga.YGEdge.YGEdgeEnd
    YGEdgeHorizontal = yoga.YGEdge.YGEdgeHorizontal
    YGEdgeVertical = yoga.YGEdge.YGEdgeVertical
    YGEdgeAll = yoga.YGEdge.YGEdgeAll


class YGGutter:
    YGGutterColumn = yoga.YGGutter.YGGutterColumn
    YGGutterRow = yoga.YGGutter.YGGutterRow
    YGGutterAll = yoga.YGGutter.YGGutterAll


# Export convenience aliases
DIRECTION_INHERIT = YGDirection.YGDirectionInherit
DIRECTION_LTR = YGDirection.YGDirectionLTR
DIRECTION_RTL = YGDirection.YGDirectionRTL

FLEX_DIRECTION_COLUMN = YGFlexDirection.YGFlexDirectionColumn
FLEX_DIRECTION_COLUMN_REVERSE = YGFlexDirection.YGFlexDirectionColumnReverse
FLEX_DIRECTION_ROW = YGFlexDirection.YGFlexDirectionRow
FLEX_DIRECTION_ROW_REVERSE = YGFlexDirection.YGFlexDirectionRowReverse

JUSTIFY_FLEX_START = YGJustify.YGJustifyFlexStart
JUSTIFY_CENTER = YGJustify.YGJustifyCenter
JUSTIFY_FLEX_END = YGJustify.YGJustifyFlexEnd
JUSTIFY_SPACE_BETWEEN = YGJustify.YGJustifySpaceBetween
JUSTIFY_SPACE_AROUND = YGJustify.YGJustifySpaceAround
JUSTIFY_SPACE_EVENLY = YGJustify.YGJustifySpaceEvenly

ALIGN_AUTO = YGAlign.YGAlignAuto
ALIGN_FLEX_START = YGAlign.YGAlignFlexStart
ALIGN_CENTER = YGAlign.YGAlignCenter
ALIGN_FLEX_END = YGAlign.YGAlignFlexEnd
ALIGN_STRETCH = YGAlign.YGAlignStretch
ALIGN_BASELINE = YGAlign.YGAlignBaseline
ALIGN_SPACE_BETWEEN = YGAlign.YGAlignSpaceBetween
ALIGN_SPACE_AROUND = YGAlign.YGAlignSpaceAround
ALIGN_SPACE_EVENLY = YGAlign.YGAlignSpaceEvenly

WRAP_NO_WRAP = YGWrap.YGWrapNoWrap
WRAP_WRAP = YGWrap.YGWrapWrap
WRAP_WRAP_REVERSE = YGWrap.YGWrapWrapReverse

POSITION_TYPE_STATIC = YGPositionType.YGPositionTypeStatic
POSITION_TYPE_RELATIVE = YGPositionType.YGPositionTypeRelative
POSITION_TYPE_ABSOLUTE = YGPositionType.YGPositionTypeAbsolute

DISPLAY_FLEX = YGDisplay.YGDisplayFlex
DISPLAY_NONE = YGDisplay.YGDisplayNone

EDGE_LEFT = YGEdge.YGEdgeLeft
EDGE_TOP = YGEdge.YGEdgeTop
EDGE_RIGHT = YGEdge.YGEdgeRight
EDGE_BOTTOM = YGEdge.YGEdgeBottom
EDGE_START = YGEdge.YGEdgeStart
EDGE_END = YGEdge.YGEdgeEnd
EDGE_HORIZONTAL = YGEdge.YGEdgeHorizontal
EDGE_VERTICAL = YGEdge.YGEdgeVertical
EDGE_ALL = YGEdge.YGEdgeAll

GUTTER_COLUMN = YGGutter.YGGutterColumn
GUTTER_ROW = YGGutter.YGGutterRow
GUTTER_ALL = YGGutter.YGGutterAll

# Undefined value
UNDEFINED = yoga.YGUndefined


class LayoutNode:
    """
    Wrapper around yoga.Node providing the project's original API.
    """

    def __init__(self, config: YogaConfig | None = None):
        """Initialize a LayoutNode with optional config."""
        self._node = YogaNode(config or YogaConfig())
        self._measure_func: Callable[[float, float], tuple[float, float]] | None = None

    @staticmethod
    def create(config: YogaConfig | None = None) -> LayoutNode:
        """Create a new LayoutNode."""
        return LayoutNode(config)

    # Child management
    def insert_child(self, child: LayoutNode, index: int) -> None:
        """Insert a child node at the given index."""
        yoga.YGNodeInsertChild(self._node, child._node, index)

    def remove_child(self, child: LayoutNode) -> None:
        """Remove a child node."""
        yoga.YGNodeRemoveChild(self._node, child._node)

    def get_child_count(self) -> int:
        """Get the number of children."""
        return yoga.YGNodeGetChildCount(self._node)

    # Dirty state
    def mark_dirty(self) -> None:
        """Mark the node as dirty for re-layout."""
        self._node.markDirtyAndPropagate()

    # Measure function
    def set_measure_func(self, func: Callable[[float, float], tuple[float, float]] | None) -> None:
        """Set the measure function for this node."""
        self._measure_func = func
        if func is not None:
            def measure_wrapper(node, width: float, width_mode, height: float, height_mode) -> yoga.YGSize:
                result = func(width, height)
                return yoga.YGSize(width=result[0], height=result[1])
            self._node.setMeasureFunc(measure_wrapper)
        else:
            self._node.setMeasureFunc(None)

    # Layout calculation
    def calculate_layout(
        self,
        width: float = UNDEFINED,
        height: float = UNDEFINED,
        direction: int = DIRECTION_LTR,
    ) -> None:
        """Calculate the layout for this node and its children."""
        dir_enum = yoga.YGDirection(direction)
        yoga.YGNodeCalculateLayout(self._node, width, height, dir_enum)

    # Dimension setters
    def set_width(self, width: float) -> None:
        """Set the width in points."""
        yoga.YGNodeStyleSetWidth(self._node, width)

    def set_height(self, height: float) -> None:
        """Set the height in points."""
        yoga.YGNodeStyleSetHeight(self._node, height)

    def set_width_percent(self, percent: float) -> None:
        """Set the width as a percentage."""
        yoga.YGNodeStyleSetWidthPercent(self._node, percent)

    def set_height_percent(self, percent: float) -> None:
        """Set the height as a percentage."""
        yoga.YGNodeStyleSetHeightPercent(self._node, percent)

    def set_width_auto(self) -> None:
        """Set width to auto."""
        yoga.YGNodeStyleSetWidthAuto(self._node)

    def set_height_auto(self) -> None:
        """Set height to auto."""
        yoga.YGNodeStyleSetHeightAuto(self._node)

    # Min dimension setters
    def set_min_width(self, width: float) -> None:
        """Set minimum width."""
        yoga.YGNodeStyleSetMinWidth(self._node, width)

    def set_min_height(self, height: float) -> None:
        """Set minimum height."""
        yoga.YGNodeStyleSetMinHeight(self._node, height)

    def set_min_width_percent(self, percent: float) -> None:
        """Set minimum width as percentage."""
        yoga.YGNodeStyleSetMinWidthPercent(self._node, percent)

    def set_min_height_percent(self, percent: float) -> None:
        """Set minimum height as percentage."""
        yoga.YGNodeStyleSetMinHeightPercent(self._node, percent)

    # Max dimension setters
    def set_max_width(self, width: float) -> None:
        """Set maximum width."""
        yoga.YGNodeStyleSetMaxWidth(self._node, width)

    def set_max_height(self, height: float) -> None:
        """Set maximum height."""
        yoga.YGNodeStyleSetMaxHeight(self._node, height)

    def set_max_width_percent(self, percent: float) -> None:
        """Set maximum width as percentage."""
        yoga.YGNodeStyleSetMaxWidthPercent(self._node, percent)

    def set_max_height_percent(self, percent: float) -> None:
        """Set maximum height as percentage."""
        yoga.YGNodeStyleSetMaxHeightPercent(self._node, percent)

    # Margin setters
    def set_margin(self, edge: int, value: float) -> None:
        """Set margin for an edge."""
        yoga.YGNodeStyleSetMargin(self._node, yoga.YGEdge(edge), value)

    def set_margin_percent(self, edge: int, percent: float) -> None:
        """Set margin as percentage."""
        yoga.YGNodeStyleSetMarginPercent(self._node, yoga.YGEdge(edge), percent)

    def set_margin_auto(self, edge: int) -> None:
        """Set margin to auto."""
        yoga.YGNodeStyleSetMarginAuto(self._node, yoga.YGEdge(edge))

    # Padding setters
    def set_padding(self, edge: int, value: float) -> None:
        """Set padding for an edge."""
        yoga.YGNodeStyleSetPadding(self._node, yoga.YGEdge(edge), value)

    def set_padding_percent(self, edge: int, percent: float) -> None:
        """Set padding as percentage."""
        yoga.YGNodeStyleSetPaddingPercent(self._node, yoga.YGEdge(edge), percent)

    # Border setters
    def set_border(self, edge: int, value: float) -> None:
        """Set border width for an edge."""
        yoga.YGNodeStyleSetBorder(self._node, yoga.YGEdge(edge), value)

    # Position setters
    def set_position(self, edge: int, value: float) -> None:
        """Set position for an edge."""
        yoga.YGNodeStyleSetPosition(self._node, yoga.YGEdge(edge), value)

    def set_position_percent(self, edge: int, percent: float) -> None:
        """Set position as percentage."""
        yoga.YGNodeStyleSetPositionPercent(self._node, yoga.YGEdge(edge), percent)

    # Flex properties
    def set_flex_direction(self, direction: int) -> None:
        """Set flex direction."""
        yoga.YGNodeStyleSetFlexDirection(self._node, yoga.YGFlexDirection(direction))

    def set_flex_grow(self, grow: float) -> None:
        """Set flex grow."""
        yoga.YGNodeStyleSetFlexGrow(self._node, grow)

    def set_flex_shrink(self, shrink: float) -> None:
        """Set flex shrink."""
        yoga.YGNodeStyleSetFlexShrink(self._node, shrink)

    def set_flex_basis(self, basis: float) -> None:
        """Set flex basis."""
        if math.isnan(basis):
            yoga.YGNodeStyleSetFlexBasisAuto(self._node)
        else:
            yoga.YGNodeStyleSetFlexBasis(self._node, basis)

    def set_flex_basis_percent(self, percent: float) -> None:
        """Set flex basis as percentage."""
        yoga.YGNodeStyleSetFlexBasisPercent(self._node, percent)

    def set_flex_wrap(self, wrap: int) -> None:
        """Set flex wrap."""
        yoga.YGNodeStyleSetFlexWrap(self._node, yoga.YGWrap(wrap))

    # Alignment properties
    def set_align_items(self, align: int) -> None:
        """Set align items."""
        yoga.YGNodeStyleSetAlignItems(self._node, yoga.YGAlign(align))

    def set_align_self(self, align: int) -> None:
        """Set align self."""
        yoga.YGNodeStyleSetAlignSelf(self._node, yoga.YGAlign(align))

    def set_align_content(self, align: int) -> None:
        """Set align content."""
        yoga.YGNodeStyleSetAlignContent(self._node, yoga.YGAlign(align))

    def set_justify_content(self, justify: int) -> None:
        """Set justify content."""
        yoga.YGNodeStyleSetJustifyContent(self._node, yoga.YGJustify(justify))

    # Display and position type
    def set_display(self, display: int) -> None:
        """Set display mode."""
        yoga.YGNodeStyleSetDisplay(self._node, yoga.YGDisplay(display))

    def set_position_type(self, position_type: int) -> None:
        """Set position type."""
        yoga.YGNodeStyleSetPositionType(self._node, yoga.YGPositionType(position_type))

    # Gap
    def set_gap(self, gutter: int, value: float) -> None:
        """Set gap."""
        yoga.YGNodeStyleSetGap(self._node, yoga.YGGutter(gutter), value)

    # Aspect ratio
    def set_aspect_ratio(self, ratio: float) -> None:
        """Set aspect ratio."""
        yoga.YGNodeStyleSetAspectRatio(self._node, ratio)

    # Computed values getters
    def get_computed_width(self) -> float:
        """Get computed width."""
        return yoga.YGNodeLayoutGetWidth(self._node)

    def get_computed_height(self) -> float:
        """Get computed height."""
        return yoga.YGNodeLayoutGetHeight(self._node)

    def get_computed_left(self) -> float:
        """Get computed left position."""
        return yoga.YGNodeLayoutGetLeft(self._node)

    def get_computed_top(self) -> float:
        """Get computed top position."""
        return yoga.YGNodeLayoutGetTop(self._node)

    def get_computed_padding(self, edge: int) -> float:
        """Get computed padding for an edge."""
        return yoga.YGNodeLayoutGetPadding(self._node, yoga.YGEdge(edge))

    def get_computed_margin(self, edge: int) -> float:
        """Get computed margin for an edge."""
        return yoga.YGNodeLayoutGetMargin(self._node, yoga.YGEdge(edge))

    def get_computed_border(self, edge: int) -> float:
        """Get computed border for an edge."""
        return yoga.YGNodeLayoutGetBorder(self._node, yoga.YGEdge(edge))

    def get_display(self) -> int:
        """Get the display mode."""
        return int(yoga.YGNodeStyleGetDisplay(self._node))

    # Free resources
    def free(self) -> None:
        """Free the node and its resources."""
        # In yoga-layout-python, nodes are garbage collected automatically
        # This method is kept for API compatibility
        pass

    def free_recursive(self) -> None:
        """Free the node and all its children recursively."""
        yoga.YGNodeFreeRecursive(self._node)

    # Access to underlying node for advanced usage
    @property
    def _internal_node(self) -> Node:
        """Get the underlying yoga Node."""
        return self._node


# Create Node alias for compatibility
class NodeWrapper:
    """Factory for creating LayoutNode instances."""

    @staticmethod
    def create(config: YogaConfig | None = None) -> LayoutNode:
        """Create a new LayoutNode."""
        return LayoutNode.create(config)


# Export Node as an alias
Node = NodeWrapper

# Export Config as an alias
Config = YogaConfig


__all__ = [
    # Classes
    "LayoutNode",
    "Node",
    "Config",
    # Direction
    "YGDirection",
    "DIRECTION_INHERIT",
    "DIRECTION_LTR",
    "DIRECTION_RTL",
    # Flex Direction
    "YGFlexDirection",
    "FLEX_DIRECTION_COLUMN",
    "FLEX_DIRECTION_COLUMN_REVERSE",
    "FLEX_DIRECTION_ROW",
    "FLEX_DIRECTION_ROW_REVERSE",
    # Justify
    "YGJustify",
    "JUSTIFY_FLEX_START",
    "JUSTIFY_CENTER",
    "JUSTIFY_FLEX_END",
    "JUSTIFY_SPACE_BETWEEN",
    "JUSTIFY_SPACE_AROUND",
    "JUSTIFY_SPACE_EVENLY",
    # Align
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
    # Wrap
    "YGWrap",
    "WRAP_NO_WRAP",
    "WRAP_WRAP",
    "WRAP_WRAP_REVERSE",
    # Position Type
    "YGPositionType",
    "POSITION_TYPE_STATIC",
    "POSITION_TYPE_RELATIVE",
    "POSITION_TYPE_ABSOLUTE",
    # Display
    "YGDisplay",
    "DISPLAY_FLEX",
    "DISPLAY_NONE",
    # Edge
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
    # Gutter
    "YGGutter",
    "GUTTER_COLUMN",
    "GUTTER_ROW",
    "GUTTER_ALL",
    # Other
    "UNDEFINED",
]
