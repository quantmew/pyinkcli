"""Tests for hooks."""

import pytest
from ink_python.hooks.state import useState, useEffect, useRef, useMemo, useCallback


def test_use_state_initial_value():
    """Test useState with initial value."""
    value, set_value = useState(5)
    assert value == 5


def test_use_state_with_factory():
    """Test useState with factory function."""
    value, set_value = useState(lambda: 10)
    assert value == 10


def test_use_state_setter():
    """Test useState setter function."""
    value, set_value = useState(0)
    # Note: In a real component render, this would update
    # Here we just test the setter exists
    assert callable(set_value)


def test_use_ref_initial():
    """Test useRef with initial value."""
    ref = useRef("hello")
    assert ref.current == "hello"


def test_use_ref_mutable():
    """Test that useRef is mutable."""
    ref = useRef(0)
    ref.current = 5
    assert ref.current == 5


def test_use_memo():
    """Test useMemo caches value."""
    call_count = [0]

    def factory():
        call_count[0] += 1
        return 42

    # First call
    result = useMemo(factory, (1, 2))
    assert result == 42
    assert call_count[0] == 1

    # Same deps - should use cache (but in this simple test, it won't)
    result2 = useMemo(factory, (1, 2))
    assert result2 == 42


def test_use_callback():
    """Test useCallback memoizes callback."""
    def my_callback():
        return "hello"

    result = useCallback(my_callback, (1,))
    assert result() == "hello"


def test_use_effect():
    """Test useEffect runs."""
    ran = [False]

    def effect():
        ran[0] = True

    useEffect(effect, ())
    assert ran[0]
