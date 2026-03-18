"""Tests for Box component."""

from ink_python.components.Box import Box
from ink_python.component import createElement


def test_box_creates_vnode():
    """Test that Box creates a virtual node."""
    vnode = Box(createElement("ink-text", "Hello"))
    assert vnode is not None
    assert vnode.type == "ink-box"


def test_box_with_flex_direction():
    """Test Box with flexDirection prop."""
    vnode = Box(flexDirection="column")
    assert vnode is not None
    assert vnode.props.get("style", {}).get("flexDirection") == "column"


def test_box_with_padding():
    """Test Box with padding prop."""
    vnode = Box(padding=2)
    assert vnode is not None
    assert vnode.props.get("style", {}).get("padding") == 2


def test_box_with_margin():
    """Test Box with margin prop."""
    vnode = Box(margin=1)
    assert vnode is not None
    assert vnode.props.get("style", {}).get("margin") == 1


def test_box_with_width():
    """Test Box with width prop."""
    vnode = Box(width=40)
    assert vnode is not None
    assert vnode.props.get("style", {}).get("width") == 40


def test_box_with_height():
    """Test Box with height prop."""
    vnode = Box(height=10)
    assert vnode is not None
    assert vnode.props.get("style", {}).get("height") == 10


def test_box_with_border():
    """Test Box with borderStyle prop."""
    vnode = Box(borderStyle="single")
    assert vnode is not None
    assert vnode.props.get("style", {}).get("borderStyle") == "single"


def test_box_with_background_color():
    """Test Box with backgroundColor prop."""
    vnode = Box(backgroundColor="blue")
    assert vnode is not None
    assert vnode.props.get("style", {}).get("backgroundColor") == "blue"


def test_box_with_children():
    """Test Box with children."""
    child1 = createElement("ink-text", "Child 1")
    child2 = createElement("ink-text", "Child 2")
    vnode = Box(child1, child2)
    assert vnode is not None
    assert len(vnode.children) == 2


def test_box_default_style():
    """Test Box default style values."""
    vnode = Box()
    style = vnode.props.get("style", {})
    assert style.get("flexWrap") == "nowrap"
    assert style.get("flexDirection") == "row"
    assert style.get("flexGrow") == 0
    assert style.get("flexShrink") == 1


def test_box_overflow():
    """Test Box with overflow prop."""
    vnode = Box(overflow="hidden")
    style = vnode.props.get("style", {})
    assert style.get("overflowX") == "hidden"
    assert style.get("overflowY") == "hidden"
