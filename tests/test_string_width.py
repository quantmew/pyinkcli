"""Tests for string_width utility."""

import pytest
from pyinkcli.utils.string_width import string_width, widest_line


def test_string_width_ascii():
    """Test width of ASCII characters."""
    assert string_width("hello") == 5
    assert string_width("hello world") == 11
    assert string_width("") == 0


def test_string_width_wide_chars():
    """Test width of wide characters (CJK)."""
    # CJK characters are typically double-width
    assert string_width("你好") >= 4  # At least 4 columns
    assert string_width("日本語") >= 6  # At least 6 columns


def test_string_width_emoji():
    """Test width of emoji characters."""
    # Emoji are typically double-width
    assert string_width("👋") >= 2  # At least 2 columns


def test_string_width_mixed():
    """Test width of mixed content."""
    width = string_width("hello 世界")
    assert width >= 9  # At least 5 + 1 + 4 (space + 2 wide chars)


def test_string_width_newlines():
    """Test that newlines are handled."""
    # Newlines should not contribute to width
    assert string_width("hello\nworld") == string_width("helloworld")


def test_widest_line():
    """Test widest_line function."""
    assert widest_line("hello\nworld\n!") == 5
    assert widest_line("short\nvery long line\nmedium") == 14
    assert widest_line("") == 0


def test_string_width_numbers():
    """Test width of numbers."""
    assert string_width("12345") == 5
    assert string_width("0") == 1


def test_string_width_special_chars():
    """Test width of special characters."""
    assert string_width("!@#$%") == 5
    assert string_width("   ") == 3  # Spaces
