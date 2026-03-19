"""Tests for sanitizeAnsi behavior."""

from pyinkcli.ansi_tokenizer import tokenizeAnsi
from pyinkcli.sanitize_ansi import sanitizeAnsi


def strip_ansi(text: str) -> str:
    return "".join(token.value for token in tokenizeAnsi(text) if token.type == "text")


def test_sanitize_ansi_returns_plain_text_unchanged():
    assert sanitizeAnsi("hello") == "hello"


def test_sanitize_ansi_preserves_sgr_sequences():
    assert sanitizeAnsi("A\x1b[38;5;196mB\x1b[0m") == "A\x1b[38;5;196mB\x1b[0m"


def test_sanitize_ansi_preserves_colon_sgr_sequences():
    output = sanitizeAnsi("A\x1b[38:2::255:100:0mcolor\x1b[0mB")

    assert "\x1b[38:2::255:100:0m" in output
    assert strip_ansi(output) == "AcolorB"


def test_sanitize_ansi_preserves_osc_sequences():
    text = "A\x1b]8;;https://example.com\x1b\\B"
    assert sanitizeAnsi(text) == text


def test_sanitize_ansi_preserves_osc_hyperlinks_terminated_by_c1_st():
    text = "\x1b]8;;https://example.com\x9clink\x1b]8;;\x9c"
    output = sanitizeAnsi(text)

    assert "\x1b]8;;https://example.com\x9c" in output
    assert strip_ansi(output) == "link"


def test_sanitize_ansi_preserves_c1_osc_hyperlinks_terminated_by_c1_st():
    text = "\x9d8;;https://example.com\x9clink\x9d8;;\x9c"
    assert sanitizeAnsi(text) == text


def test_sanitize_ansi_preserves_c1_osc_hyperlinks_terminated_by_escape_st():
    text = "\x9d8;;https://example.com\x1b\\link\x9d8;;\x1b\\"
    assert sanitizeAnsi(text) == text


def test_sanitize_ansi_preserves_c1_osc_hyperlinks_terminated_by_bel():
    text = "\x9d8;;https://example.com\x07link\x9d8;;\x07"
    assert sanitizeAnsi(text) == text


def test_sanitize_ansi_strips_cursor_movement():
    assert sanitizeAnsi("A\x1b[2JB\x1b[3CB") == "ABB"


def test_sanitize_ansi_strips_c1_non_sgr_csi_sequences_as_complete_units():
    output = sanitizeAnsi("A\x9b>4;2mB\x9b2 qC")

    assert "4;2m" not in output
    assert " q" not in output
    assert strip_ansi(output) == "ABC"


def test_sanitize_ansi_preserves_c1_sgr_csi_sequences():
    output = sanitizeAnsi("A\x9b31mgreen\x9b0mB")

    assert "\x9b31m" in output
    assert strip_ansi(output) == "AgreenB"


def test_sanitize_ansi_strips_private_parameter_m_sequences_that_are_not_sgr():
    output = sanitizeAnsi("A\x1b[>4;2mB")

    assert "\x1b[>4;2m" not in output
    assert strip_ansi(output) == "AB"


def test_sanitize_ansi_strips_non_sgr_csi_with_intermediate_bytes():
    assert sanitizeAnsi("A\x1b[2 qB") == "AB"


def test_sanitize_ansi_strips_dcs_and_c1_controls_but_keeps_osc():
    text = "A\x1bPpayload\x1b\\B\x80C\x1b]8;;https://example.com\x1b\\D"
    assert sanitizeAnsi(text) == "ABC\x1b]8;;https://example.com\x1b\\D"


def test_sanitize_ansi_drops_tmux_passthrough_control_string():
    text = "A\x1bPtmux;\x1b\x1b]8;;https://example.com\x1b\x1b\\\x1b\\B"
    assert sanitizeAnsi(text) == "AB"


def test_sanitize_ansi_strips_incomplete_dcs_passthrough_to_avoid_payload_leaks():
    output = sanitizeAnsi("A\x1bPtmux;\x1blink")

    assert "tmux;" not in output
    assert strip_ansi(output) == "A"


def test_sanitize_ansi_drops_pm_and_apc_control_strings():
    text = "A\x1b^payload\x1b\\B\x9fpayload\x9cC"
    assert sanitizeAnsi(text) == "ABC"


def test_sanitize_ansi_strips_esc_sos_control_strings_as_complete_units():
    output = sanitizeAnsi("A\x1bXpayload\x1b\\B")

    assert "payload" not in output
    assert strip_ansi(output) == "AB"


def test_sanitize_ansi_strips_esc_sos_control_strings_with_c1_st():
    output = sanitizeAnsi("A\x1bXpayload\x9cB")

    assert "payload" not in output
    assert strip_ansi(output) == "AB"


def test_sanitize_ansi_strips_c1_sos_control_strings_with_c1_st():
    output = sanitizeAnsi("A\x98payload\x9cB")

    assert "payload" not in output
    assert strip_ansi(output) == "AB"


def test_sanitize_ansi_strips_c1_sos_control_strings_with_escape_st():
    output = sanitizeAnsi("A\x98payload\x1b\\B")

    assert "payload" not in output
    assert strip_ansi(output) == "AB"


def test_sanitize_ansi_strips_esc_sos_with_bel_as_malformed_control_string():
    output = sanitizeAnsi("A\x1bXpayload\x07B")

    assert "payload" not in output
    assert strip_ansi(output) == "A"


def test_sanitize_ansi_strips_c1_sos_with_bel_as_malformed_control_string():
    output = sanitizeAnsi("A\x98payload\x07B")

    assert "payload" not in output
    assert strip_ansi(output) == "A"


def test_sanitize_ansi_strips_incomplete_esc_sos_to_avoid_payload_leaks():
    output = sanitizeAnsi("A\x1bXpayload")

    assert "payload" not in output
    assert strip_ansi(output) == "A"


def test_sanitize_ansi_strips_incomplete_c1_sos_to_avoid_payload_leaks():
    output = sanitizeAnsi("A\x98payload")

    assert "payload" not in output
    assert strip_ansi(output) == "A"


def test_sanitize_ansi_strips_sos_with_escaped_escape_in_payload_until_final_st():
    output = sanitizeAnsi("A\x1bXfoo\x1b\x1b\\bar\x1b\\B")

    assert "foo" not in output
    assert "bar" not in output
    assert strip_ansi(output) == "AB"


def test_sanitize_ansi_preserves_sgr_around_stripped_sos_control_strings():
    output = sanitizeAnsi("A\x1b[31mR\x1b[0m\x1bXpayload\x1b\\B")

    assert "\x1b[31m" in output
    assert "\x1b[0m" in output
    assert "payload" not in output
    assert strip_ansi(output) == "ARB"


def test_sanitize_ansi_strips_esc_st_sequences():
    output = sanitizeAnsi("A\x1b\\B")

    assert "\x1b\\" not in output
    assert strip_ansi(output) == "AB"


def test_sanitize_ansi_strips_malformed_esc_control_sequences_with_intermediates():
    output = sanitizeAnsi("A\x1b#\x07payload")

    assert "payload" not in output
    assert strip_ansi(output) == "A"


def test_sanitize_ansi_strips_incomplete_csi_after_preserving_prior_sgr_content():
    output = sanitizeAnsi("A\x1b[31mB\x1b[")

    assert "\x1b[31m" in output
    assert strip_ansi(output) == "AB"


def test_sanitize_ansi_strips_standalone_st_bytes():
    output = sanitizeAnsi("A\x9cB")

    assert "\x9c" not in output
    assert strip_ansi(output) == "AB"


def test_sanitize_ansi_strips_standalone_c1_control_characters():
    output = sanitizeAnsi("A\x85B\x8eC")

    assert "\x85" not in output
    assert "\x8e" not in output
    assert strip_ansi(output) == "ABC"
