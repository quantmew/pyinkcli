"""Tests for sanitizeAnsi integration in layout/render paths."""

from pyinkcli import Box, Text, renderToString
from pyinkcli.components._accessibility_runtime import _provide_accessibility
from pyinkcli.measure_text import measureText
from pyinkcli.render_node_to_output import render_node_to_screen_reader_output
from pyinkcli.utils.wrap_ansi import truncate_string, wrap_ansi
from pyinkcli.wrap_text import wrapText


def test_measure_text_ignores_layout_affecting_control_sequences():
    width, height = measureText("Hi\x1b[2JThere")

    assert width == len("HiThere")
    assert height == 1


def test_wrap_text_strips_cursor_controls_but_preserves_sgr():
    wrapped = wrapText("AB\x1b[2JC\x1b[31mDE\x1b[39m", 3)

    assert "\x1b[2J" not in wrapped
    assert "\x1b[31m" in wrapped
    assert "\x1b[39m" in wrapped


def test_render_to_string_sanitizes_text_before_layout():
    output = renderToString(
        Box(
            Text("Hello\x1b[2JWorld!!", background_color="red"),
            width=10,
            alignSelf="flex-start",
        )
    )

    assert "\x1b[2J" not in output
    assert output == "\x1b[41mHelloWorld\x1b[49m\n\x1b[41m!!\x1b[49m"


def test_screen_reader_output_sanitizes_control_sequences():
    vnode = Box(Text("Hello\x1b[2JWorld"))
    from pyinkcli.reconciler import createReconciler
    from pyinkcli.render_to_string import create_root_node

    root_node = create_root_node(40, 5)
    reconciler = createReconciler(root_node)
    container = reconciler.create_container(root_node)
    reconciler.update_container(vnode, container)

    with _provide_accessibility(True):
        output = render_node_to_screen_reader_output(root_node)

    assert "\x1b[2J" not in output
    assert "HelloWorld" in output


def test_wrap_ansi_public_entry_sanitizes_control_sequences():
    wrapped = wrap_ansi("AB\x1b[2JCDEF", 3, hard=True)

    assert "\x1b[2J" not in wrapped
    assert wrapped == "ABC\nDEF"


def test_truncate_string_public_entry_sanitizes_control_sequences():
    truncated = truncate_string("AB\x1b[2JCDEF", 4, "end")

    assert "\x1b[2J" not in truncated
