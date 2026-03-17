"""Tests for CLI boxes utility."""

import pytest
from ink_python.utils.cli_boxes import BOXES, BoxStyle, get_box_style


def test_box_styles_exist():
    """Test that all expected box styles exist."""
    assert "single" in BOXES
    assert "double" in BOXES
    assert "round" in BOXES
    assert "bold" in BOXES
    assert "singleDouble" in BOXES
    assert "doubleSingle" in BOXES
    assert "classic" in BOXES
    assert "arrow" in BOXES


def test_single_box_style():
    """Test single box style characters."""
    style = BOXES["single"]
    assert style.top_left == "┌"
    assert style.top == "─"
    assert style.top_right == "┐"
    assert style.right == "│"
    assert style.bottom_right == "┘"
    assert style.bottom == "─"
    assert style.bottom_left == "└"
    assert style.left == "│"


def test_double_box_style():
    """Test double box style characters."""
    style = BOXES["double"]
    assert style.top_left == "╔"
    assert style.top == "═"
    assert style.right == "║"


def test_round_box_style():
    """Test round box style characters."""
    style = BOXES["round"]
    assert style.top_left == "╭"
    assert style.bottom_left == "╰"


def test_classic_box_style():
    """Test classic box style characters."""
    style = BOXES["classic"]
    assert style.top_left == "+"
    assert style.top == "-"
    assert style.right == "|"


def test_get_box_style_by_name():
    """Test get_box_style function."""
    style = get_box_style("single")
    assert isinstance(style, BoxStyle)
    assert style.top_left == "┌"


def test_get_box_style_by_instance():
    """Test that get_box_style returns the style if already a BoxStyle."""
    style = BoxStyle(
        top_left="a",
        top="b",
        top_right="c",
        right="d",
        bottom_right="e",
        bottom="f",
        bottom_left="g",
        left="h",
    )
    result = get_box_style(style)
    assert result is style


def test_box_style_immutability():
    """Test that box styles are immutable (frozen dataclass)."""
    style = BOXES["single"]
    with pytest.raises(AttributeError):
        style.top_left = "X"
