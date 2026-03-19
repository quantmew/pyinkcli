"""Tests for Text component."""

from ink_python import renderToString
from ink_python.components.Text import Text
from ink_python.component import createElement


def test_text_creates_vnode():
    """Test that Text creates a virtual node."""
    vnode = Text("Hello")
    assert vnode is not None
    assert vnode.type == "ink-text"


def test_text_with_color():
    """Test Text with color prop."""
    vnode = Text("Hello", color="red")
    assert vnode is not None
    assert vnode.props.get("internal_transform") is not None


def test_text_with_bold():
    """Test Text with bold prop."""
    vnode = Text("Hello", bold=True)
    assert vnode is not None


def test_text_with_multiple_styles():
    """Test Text with multiple style props."""
    vnode = Text("Hello", color="green", bold=True, underline=True)
    assert vnode is not None


def test_text_empty_returns_none():
    """Test that empty text returns None."""
    vnode = Text()
    assert vnode is None


def test_text_with_children():
    """Test Text with string children."""
    vnode = Text("Hello", " ", "World")
    assert vnode is not None


def test_text_wrap_prop():
    """Test Text with wrap prop."""
    vnode = Text("Hello", wrap="truncate")
    assert vnode is not None
    style = vnode.props.get("style", {})
    assert style.get("textWrap") == "truncate"


def test_text_accepts_camel_case_background_color():
    """Test Text with JS-style backgroundColor prop."""
    output = renderToString(Text("Hello", backgroundColor="red"))
    assert "\x1b[41mHello\x1b[49m" == output


def test_text_accepts_camel_case_dim_color():
    """Test Text with JS-style dimColor prop."""
    output = renderToString(Text("Hello", dimColor=True))
    assert output == "\x1b[2mHello\x1b[22m"
