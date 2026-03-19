"""Tests for ANSI-aware output buffer behavior."""

from pyinkcli.output import (
    Output,
)


def test_slice_ansi_columns_preserves_escape_sequences():
    text = "\x1b[31mhello\x1b[39m"
    sliced = Output._slice_ansi_columns(text, 1, 4)

    assert "\x1b[31m" in sliced
    assert "ell" in sliced
    assert sliced.endswith("\x1b[0m") or sliced.endswith("\x1b[39m")


def test_output_clips_ansi_text_by_visible_columns():
    output = Output({"width": 3, "height": 1})
    output.clip({"x1": 0, "x2": 3})
    output.write(0, 0, "\x1b[31mhello\x1b[39m", {"transformers": []})

    rendered = output.get().output
    assert "hel" in rendered
    assert "\x1b[31m" in rendered


def test_output_handles_wide_characters_without_extra_gaps():
    output = Output({"width": 4, "height": 1})
    output.write(0, 0, "你a", {"transformers": []})

    rendered = output.get().output
    assert rendered.startswith("你a")


def test_slice_ansi_columns_closes_style_when_reset_is_outside_slice():
    text = "\x1b[31mhello world\x1b[39m"
    sliced = Output._slice_ansi_columns(text, 0, 5)

    assert sliced.endswith("\x1b[0m") or sliced.endswith("\x1b[39m")


def test_styled_cells_preserve_zero_width_suffixes():
    cells = Output._styled_cells("\x1b[31mA\x1b[0m\u0301")

    assert len(cells) == 1
    assert cells[0].styles == ("\x1b[31m",)
    assert cells[0].suffix == "\u0301"
    assert Output._styled_cells_to_string(cells).endswith("\u0301\x1b[39m")


def test_output_overwrite_keeps_new_styles_stable():
    output = Output({"width": 5, "height": 1})
    output.write(0, 0, "\x1b[31mabc\x1b[0m", {"transformers": []})
    output.write(1, 0, "\x1b[44mZ\x1b[0m", {"transformers": []})

    rendered = output.get().output
    assert rendered.startswith("\x1b[31ma")
    assert "\x1b[44mZ" in rendered
    assert "\x1b[49m" in rendered


def test_styled_cells_to_string_re_emits_style_stack_transitions():
    rendered = Output._styled_cells_to_string(
        [
            Output._styled_cells("\x1b[31mA")[0],
            Output._styled_cells("\x1b[31m\x1b[44mB")[0],
            Output._styled_cells("C")[0],
        ]
    )

    assert rendered.startswith("\x1b[31mA")
    assert "\x1b[44mB" in rendered
    assert rendered.endswith("\x1b[39m\x1b[49mC")


def test_styled_cells_support_extended_foreground_and_background_colors():
    cells = Output._styled_cells("\x1b[38;5;196mR\x1b[48;2;1;2;3mG\x1b[49mB")

    assert cells[0].styles == ("\x1b[38;5;196m",)
    assert cells[1].styles == ("\x1b[38;5;196m", "\x1b[48;2;1;2;3m")
    assert cells[2].styles == ("\x1b[38;5;196m",)


def test_styled_cells_to_string_preserves_extended_color_sequences():
    rendered = Output._styled_cells_to_string(Output._styled_cells("\x1b[38;5;196mR\x1b[48;5;9mG\x1b[49mB"))

    assert "\x1b[38;5;196mR" in rendered
    assert "\x1b[48;5;9mG" in rendered
    assert rendered.endswith("B\x1b[39m")


def test_output_write_strips_layout_affecting_control_sequences():
    output = Output({"width": 10, "height": 1})
    output.write(0, 0, "A\x1b[2JB", {"transformers": []})

    rendered = output.get().output
    assert "\x1b[2J" not in rendered
    assert rendered == "AB"


def test_output_sanitizes_transformer_output():
    output = Output({"width": 10, "height": 1})
    output.write(
        0,
        0,
        "AB",
        {"transformers": [lambda s, index: "A\x1b[2JB"]},
    )

    rendered = output.get().output
    assert "\x1b[2J" not in rendered
    assert rendered == "AB"
