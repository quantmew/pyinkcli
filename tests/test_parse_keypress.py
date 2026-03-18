from ink_python.parse_keypress import (
    parseKeypress,
    parseKittyKeypress,
    parseKittySpecialKey,
)


def test_parse_keypress_arrow_sequence():
    key = parseKeypress("\x1b[A")

    assert key.name == "up"
    assert key.ctrl is False
    assert key.shift is False


def test_parse_keypress_ctrl_letter():
    key = parseKeypress("\x03")

    assert key.name == "c"
    assert key.ctrl is True


def test_parse_keypress_shift_letter():
    key = parseKeypress("A")

    assert key.name == "a"
    assert key.shift is True


def test_parse_kitty_keypress_sets_modifiers_and_event_type():
    key = parseKittyKeypress("\x1b[97;5:2u")

    assert key is not None
    assert key.name == "a"
    assert key.ctrl is True
    assert key.eventType == "repeat"
    assert key.isKittyProtocol is True


def test_parse_kitty_special_key_arrow_sequence():
    key = parseKittySpecialKey("\x1b[1;5:1A")

    assert key is not None
    assert key.name == "up"
    assert key.ctrl is True
    assert key.eventType == "press"


def test_parse_keypress_rejects_invalid_kitty_codepoint_safely():
    key = parseKeypress("\x1b[55296;1u")

    assert key.name == ""
    assert key.isKittyProtocol is True
    assert key.isPrintable is False


def test_parse_kitty_keypress_maps_extended_special_names():
    key = parseKittyKeypress("\x1b[57361;1u")

    assert key is not None
    assert key.name == "printscreen"
    assert key.isPrintable is False


def test_parse_keypress_accepts_single_high_bit_byte_as_meta_sequence():
    key = parseKeypress(bytes([0xE1]))

    assert key.meta is True
    assert key.name == "a"


def test_parse_keypress_accepts_ascii_bytes():
    key = parseKeypress(b"A")

    assert key.name == "a"
    assert key.shift is True
