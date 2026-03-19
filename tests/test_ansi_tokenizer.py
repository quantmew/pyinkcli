"""Tests for ANSI tokenizer behavior."""

from pyinkcli.ansi_tokenizer import hasAnsiControlCharacters, tokenizeAnsi


def test_tokenize_plain_text():
    tokens = tokenizeAnsi("hello")

    assert [(token.type, token.value) for token in tokens] == [("text", "hello")]


def test_tokenize_csi_sequence():
    tokens = tokenizeAnsi("A\x1b[38;5;196mB")

    assert [token.type for token in tokens] == ["text", "csi", "text"]
    assert tokens[1].value == "\x1b[38;5;196m"
    assert tokens[1].parameter_string == "38;5;196"
    assert tokens[1].final_character == "m"


def test_tokenize_osc_sequence():
    tokens = tokenizeAnsi("A\x1b]8;;https://example.com\x1b\\B")

    assert [token.type for token in tokens] == ["text", "osc", "text"]
    assert tokens[1].value == "\x1b]8;;https://example.com\x1b\\"


def test_tokenize_c1_osc_with_c1_st_terminator():
    tokens = tokenizeAnsi("A\x9d8;;https://example.com\x9cB")

    assert [token.type for token in tokens] == ["text", "osc", "text"]
    assert tokens[1].value == "\x9d8;;https://example.com\x9c"


def test_tokenize_c1_osc_with_escape_st_terminator():
    tokens = tokenizeAnsi("A\x9d8;;https://example.com\x1b\\B")

    assert [token.type for token in tokens] == ["text", "osc", "text"]
    assert tokens[1].value == "\x9d8;;https://example.com\x1b\\"


def test_tokenize_incomplete_csi_as_invalid():
    tokens = tokenizeAnsi("A\x1b[")

    assert [(token.type, token.value) for token in tokens] == [
        ("text", "A"),
        ("invalid", "\x1b["),
    ]


def test_tokenize_c1_csi_sequence():
    tokens = tokenizeAnsi("A\x9b31mB")

    assert [token.type for token in tokens] == ["text", "csi", "text"]
    assert tokens[1].parameter_string == "31"
    assert tokens[1].final_character == "m"


def test_has_ansi_control_characters_detects_escape_and_c1():
    assert hasAnsiControlCharacters("A\x1b[31mB") is True
    assert hasAnsiControlCharacters("A\x90payload\x1b\\B") is True
    assert hasAnsiControlCharacters("plain text") is False


def test_tokenize_dcs_control_string():
    tokens = tokenizeAnsi("A\x1bPpayload\x07still-payload\x1b\\B")

    assert [token.type for token in tokens] == ["text", "dcs", "text"]
    assert "\x07" in tokens[1].value
    assert tokens[1].value.endswith("\x1b\\")


def test_tokenize_c1_osc_with_bell_terminator():
    tokens = tokenizeAnsi("A\x9d8;;https://example.com\x07B")

    assert [token.type for token in tokens] == ["text", "osc", "text"]
    assert tokens[1].value == "\x9d8;;https://example.com\x07"


def test_tokenize_esc_st_sequence_as_esc_token():
    tokens = tokenizeAnsi("A\x1b\\B")

    assert [token.type for token in tokens] == ["text", "esc", "text"]
    assert tokens[1].value == "\x1b\\"
    assert tokens[1].final_character == "\\"


def test_tokenize_incomplete_escape_intermediate_sequence_as_invalid():
    tokens = tokenizeAnsi("A\x1b#")

    assert [(token.type, token.value) for token in tokens] == [
        ("text", "A"),
        ("invalid", "\x1b#"),
    ]


def test_tokenize_incomplete_c1_osc_as_invalid():
    tokens = tokenizeAnsi("A\x9d8;;https://example.com")

    assert [(token.type, token.value) for token in tokens] == [
        ("text", "A"),
        ("invalid", "\x9d8;;https://example.com"),
    ]


def test_tokenize_lone_escape_before_non_final_byte_is_ignored():
    tokens = tokenizeAnsi("A\x1b\x07B")

    assert [(token.type, token.value) for token in tokens] == [
        ("text", "A"),
        ("text", "\x07B"),
    ]


def test_tokenize_string_terminator_and_c1_control():
    tokens = tokenizeAnsi("A\x9c\x80B")

    assert [(token.type, token.value) for token in tokens] == [
        ("text", "A"),
        ("st", "\x9c"),
        ("c1", "\x80"),
        ("text", "B"),
    ]


def test_tokenize_tmux_dcs_passthrough_as_single_control_string():
    tokens = tokenizeAnsi(
        "A\x1bPtmux;\x1b\x1b]8;;https://example.com\x1b\x1b\\\x1b\\B"
    )

    assert [token.type for token in tokens] == ["text", "dcs", "text"]
    assert tokens[1].value.startswith("\x1bPtmux;")
    assert tokens[1].value.endswith("\x1b\\")


def test_tokenize_escape_sos_with_bell_terminator_as_invalid():
    tokens = tokenizeAnsi("A\x1bXpayload\x07B")

    assert [(token.type, token.value) for token in tokens] == [
        ("text", "A"),
        ("invalid", "\x1bXpayload\x07B"),
    ]


def test_tokenize_escape_sos_with_escape_st_terminator():
    tokens = tokenizeAnsi("A\x1bXpayload\x1b\\B")

    assert [token.type for token in tokens] == ["text", "sos", "text"]
    assert tokens[1].value == "\x1bXpayload\x1b\\"


def test_tokenize_escape_sos_with_c1_st_terminator():
    tokens = tokenizeAnsi("A\x1bXpayload\x9cB")

    assert [token.type for token in tokens] == ["text", "sos", "text"]
    assert tokens[1].value == "\x1bXpayload\x9c"


def test_tokenize_c1_sos_with_escape_st_terminator():
    tokens = tokenizeAnsi("A\x98payload\x1b\\B")

    assert [token.type for token in tokens] == ["text", "sos", "text"]
    assert tokens[1].value == "\x98payload\x1b\\"


def test_tokenize_c1_sos_with_c1_st_terminator():
    tokens = tokenizeAnsi("A\x98payload\x9cB")

    assert [token.type for token in tokens] == ["text", "sos", "text"]
    assert tokens[1].value == "\x98payload\x9c"


def test_tokenize_incomplete_c1_sos_as_invalid():
    tokens = tokenizeAnsi("A\x98payload")

    assert [(token.type, token.value) for token in tokens] == [
        ("text", "A"),
        ("invalid", "\x98payload"),
    ]


def test_tokenize_incomplete_escape_sos_as_invalid():
    tokens = tokenizeAnsi("A\x1bXpayload")

    assert [(token.type, token.value) for token in tokens] == [
        ("text", "A"),
        ("invalid", "\x1bXpayload"),
    ]


def test_tokenize_escape_pm_with_escaped_escape_in_payload():
    tokens = tokenizeAnsi("A\x1b^foo\x1b\x1b\\bar\x1b\\B")

    assert [token.type for token in tokens] == ["text", "pm", "text"]
    assert "\x1b\x1b\\" in tokens[1].value
    assert tokens[1].value.endswith("\x1b\\")


def test_tokenize_incomplete_escape_apc_as_invalid():
    tokens = tokenizeAnsi("A\x1b_payload")

    assert [(token.type, token.value) for token in tokens] == [
        ("text", "A"),
        ("invalid", "\x1b_payload"),
    ]


def test_tokenize_c1_pm_with_c1_st_terminator():
    tokens = tokenizeAnsi("A\x9epayload\x9cB")

    assert [token.type for token in tokens] == ["text", "pm", "text"]
    assert tokens[1].value == "\x9epayload\x9c"


def test_tokenize_c1_apc_with_escape_st_terminator():
    tokens = tokenizeAnsi("A\x9fpayload\x1b\\B")

    assert [token.type for token in tokens] == ["text", "apc", "text"]
    assert tokens[1].value == "\x9fpayload\x1b\\"


def test_tokenize_standalone_c1_controls_as_c1_tokens():
    tokens = tokenizeAnsi("A\x85B\x8eC")

    assert [(token.type, token.value) for token in tokens] == [
        ("text", "A"),
        ("c1", "\x85"),
        ("text", "B"),
        ("c1", "\x8e"),
        ("text", "C"),
    ]
