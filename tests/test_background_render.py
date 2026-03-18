"""Tests for background rendering parity."""

import io

from ink_python import Box, Text, renderToString
from ink_python import render


BG_RED = "\x1b[41m"
BG_YELLOW = "\x1b[43m"
BG_BLUE = "\x1b[44m"
BG_RESET = "\x1b[49m"


def test_multiple_text_nodes_share_continuous_box_background():
    output = renderToString(
        Box(
            Text("Hello "),
            Text("World"),
            background_color="yellow",
            alignSelf="flex-start",
        )
    )

    assert output == f"{BG_YELLOW}Hello World{BG_RESET}"


def test_nested_background_transitions_do_not_insert_intermediate_resets():
    output = renderToString(
        Box(
            Box(
                Text("Outer: "),
                Box(
                    Text("Inner: "),
                    Text("Explicit", background_color="red"),
                    background_color="blue",
                ),
                background_color="yellow",
            ),
            alignSelf="flex-start",
        )
    )

    assert output == f"{BG_YELLOW}Outer: {BG_BLUE}Inner: {BG_RED}Explicit{BG_RESET}"


def test_box_background_fills_wrapped_lines_to_full_width():
    output = renderToString(
        Box(
            Text("Hello World!!"),
            background_color="red",
            width=10,
            alignSelf="flex-start",
        )
    )

    assert output == f"{BG_RED}Hello     {BG_RESET}\n{BG_RED}World!!   {BG_RESET}"


def test_text_only_background_does_not_fill_box_width():
    output = renderToString(
        Box(
            Text("Hello World!!", background_color="red"),
            width=10,
            alignSelf="flex-start",
        )
    )

    assert output == f"{BG_RED}Hello {BG_RESET}\n{BG_RED}World!!{BG_RESET}"


def test_box_background_with_border_fills_content_area():
    output = renderToString(
        Box(
            Text("Hi"),
            background_color="cyan",
            borderStyle="round",
            width=10,
            height=5,
            alignSelf="flex-start",
        )
    )

    assert "Hi" in output
    assert "\x1b[46m" in output
    assert BG_RESET in output
    assert "╭" in output
    assert "╮" in output


def test_box_background_with_padding_fills_padded_area():
    output = renderToString(
        Box(
            Text("Hi"),
            background_color="magenta",
            padding=1,
            width=10,
            height=5,
            alignSelf="flex-start",
        )
    )

    assert output.startswith("\x1b[45m          \x1b[49m")
    assert "\x1b[45m Hi       \x1b[49m" in output


class _TTYStringIO(io.StringIO):
    def isatty(self) -> bool:
        return True


def test_box_background_updates_on_rerender():
    stdout = _TTYStringIO()
    stdin = _TTYStringIO()

    app = render(
        Box(Text("Hello"), alignSelf="flex-start"),
        stdout=stdout,
        stdin=stdin,
        debug=True,
    )
    assert stdout.getvalue() == "Hello"

    stdout.seek(0)
    stdout.truncate(0)
    app.render(Box(Text("Hello"), background_color="green", alignSelf="flex-start"))
    assert stdout.getvalue() == "\x1b[42mHello\x1b[49m"

    stdout.seek(0)
    stdout.truncate(0)
    app.render(Box(Text("Hello"), alignSelf="flex-start"))
    assert stdout.getvalue() == "Hello"

    app.unmount()
