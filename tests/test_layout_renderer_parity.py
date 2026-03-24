from __future__ import annotations

import io

from pyinkcli import Box, Text, render, renderToString


class _Stream(io.StringIO):
    def isatty(self) -> bool:
        return False


def test_render_to_string_preserves_padding_left_without_explicit_width() -> None:
    output = renderToString(Box(Text("A"), paddingLeft=2))

    assert output == "  A"


def test_render_to_string_applies_column_gap_between_children() -> None:
    output = renderToString(
        Box(
            Text("Header"),
            Text("Body"),
            flexDirection="column",
            gap=1,
        )
    )

    assert output == "Header\n\nBody"


def test_interactive_and_render_to_string_share_box_layout_semantics() -> None:
    node = Box(
        Text("Title"),
        Text("Body"),
        flexDirection="column",
        gap=1,
        borderStyle="round",
        paddingX=1,
    )

    stdout = _Stream()
    stdin = _Stream()
    app = render(node, stdout=stdout, stdin=stdin, debug=True)
    try:
        assert stdout.getvalue() == renderToString(node)
    finally:
        app.unmount()


def test_render_to_string_honors_percent_height_constraints() -> None:
    output = renderToString(
        Box(
            Box(Text("Header"), borderStyle="round", paddingX=1, paddingY=1),
            Box(Text("Logs"), borderStyle="single", paddingX=1, paddingY=1, marginTop=1),
            Box(
                *[Text(f"Row {index}") for index in range(20)],
                borderStyle="single",
                paddingX=1,
                paddingY=1,
                marginTop=1,
                flexGrow=1,
                flexDirection="column",
            ),
            Box(Text("Footer"), borderStyle="round", paddingX=1, marginTop=1),
            flexDirection="column",
            height="100%",
        ),
        columns=40,
        rows=12,
    )

    assert len(output.splitlines()) == 12
    assert "Header" in output
    assert "Logs" in output
