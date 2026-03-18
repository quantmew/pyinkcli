"""Tests for the streaming input parser."""

from ink_python.input_parser import (
    InputParser,
    parseCsiSequence,
    parseEscapeSequence,
    parseKeypresses,
    parseSs3Sequence,
)


def test_parser_emits_plain_input():
    parser = InputParser()

    events = parser.feed("ab")

    assert [event.kind for event in events] == ["input", "input"]
    assert [event.data for event in events] == ["a", "b"]


def test_parser_keeps_escape_sequence_until_complete():
    parser = InputParser()

    assert parser.feed("\x1b") == []
    events = parser.feed("[A")

    assert len(events) == 1
    assert events[0].kind == "input"
    assert events[0].data == "\x1b[A"


def test_parser_extracts_bracketed_paste():
    parser = InputParser()

    events = parser.feed("\x1b[200~hello\nworld\x1b[201~")

    assert len(events) == 1
    assert events[0].kind == "paste"
    assert events[0].data == "hello\nworld"


def test_parser_extracts_bracketed_paste_with_mixed_cjk_text() -> None:
    parser = InputParser()

    events = parser.feed("\x1b[200~hello中文\nworld\x1b[201~")

    assert len(events) == 1
    assert events[0].kind == "paste"
    assert events[0].data == "hello中文\nworld"


def test_parser_extracts_incremental_bracketed_paste_character_by_character() -> None:
    parser = InputParser()
    events = []

    for char in "\x1b[200~hello中文\nworld\x1b[201~":
        events.extend(parser.feed(char))

    assert len(events) == 1
    assert events[0].kind == "paste"
    assert events[0].data == "hello中文\nworld"


def test_helper_parses_csi_and_ss3_sequences():
    assert parseCsiSequence("\x1b[1;5Arest") == "\x1b[1;5A"
    assert parseSs3Sequence("\x1bOArest") == "\x1bOA"
    assert parseEscapeSequence("\x1b[3~rest") == "\x1b[3~"


def test_parse_keypresses_splits_combined_delete_backspace():
    events = parseKeypresses("\x7f\x08")

    assert [event.data for event in events] == ["\x7f", "\x08"]
