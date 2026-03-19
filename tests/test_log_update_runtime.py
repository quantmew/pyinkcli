"""Tests for log update runtime behavior."""

from pyinkcli.log_update import LogUpdate
from pyinkcli.utils.ansi_escapes import (
    cursor_down,
    cursor_next_line,
    cursor_to,
    cursor_up,
    erase_lines,
    hide_cursor_escape,
    show_cursor_escape,
)


class FakeStream:
    def __init__(self) -> None:
        self.writes: list[str] = []

    def write(self, data: str) -> None:
        self.writes.append(data)

    def flush(self) -> None:
        return None


class FakeTTYStream(FakeStream):
    def isatty(self) -> bool:
        return True


def test_standard_log_update_skips_identical_output():
    stream = FakeStream()
    log = LogUpdate(stream)

    assert log("Hello\n") is True
    assert log("Hello\n") is False
    assert len(stream.writes) == 1


def test_standard_log_update_normalizes_newlines_for_tty_streams():
    stream = FakeTTYStream()
    log = LogUpdate(stream)

    log("Line 1\nLine 2\n")

    assert stream.writes[0] == hide_cursor_escape + "Line 1\r\nLine 2\r\n"


def test_standard_log_update_hides_cursor_once_and_done_shows_it_for_tty_streams():
    stream = FakeTTYStream()
    log = LogUpdate(stream)

    log("Line 1\n")
    log("Line 2\n")
    log.done()

    assert stream.writes[0] == hide_cursor_escape + "Line 1\r\n"
    assert stream.writes[1].count(hide_cursor_escape) == 0
    assert stream.writes[1].endswith("Line 2\r\n")
    assert stream.writes[2] == show_cursor_escape


def test_log_update_done_without_prior_render_does_not_show_cursor():
    stream = FakeTTYStream()
    log = LogUpdate(stream)

    log.done()

    assert stream.writes == []


def test_standard_log_update_positions_cursor_after_output():
    stream = FakeStream()
    log = LogUpdate(stream)

    log.set_cursor_position((5, 1))
    log("Line 1\nLine 2\nLine 3\n")

    assert stream.writes[0].endswith(cursor_up(2) + cursor_to(5) + show_cursor_escape)


def test_standard_log_update_hides_cursor_before_rewrite_when_previously_shown():
    stream = FakeStream()
    log = LogUpdate(stream)

    log.set_cursor_position((0, 0))
    log("Hello\n")
    log.set_cursor_position((0, 0))
    log("World\n")

    second_write = stream.writes[1]
    assert second_write.startswith(hide_cursor_escape)
    assert second_write.endswith(cursor_up(1) + cursor_to(0) + show_cursor_escape)


def test_standard_log_update_same_output_cursor_move_emits_cursor_only_sequence():
    stream = FakeStream()
    log = LogUpdate(stream)

    log.set_cursor_position((2, 0))
    log("Hello\n")
    log.set_cursor_position((3, 0))
    log("Hello\n")

    second_write = stream.writes[1]
    assert second_write.startswith(hide_cursor_escape)
    assert second_write.endswith(cursor_to(3) + show_cursor_escape)


def test_incremental_log_update_updates_only_changed_suffix():
    stream = FakeStream()
    log = LogUpdate(stream, incremental=True)

    log("Line 1\nLine 2\n")
    log("Line 1\nUpdated\n")

    assert len(stream.writes) == 2
    assert cursor_next_line() in stream.writes[1]
    assert "Updated" in stream.writes[1]


def test_incremental_log_update_positions_cursor_after_update():
    stream = FakeStream()
    log = LogUpdate(stream, incremental=True)

    log.set_cursor_position((2, 0))
    log("Line 1\nLine 2\nLine 3\n")
    log.set_cursor_position((2, 0))
    log("Line 1\nUpdated\nLine 3\n")

    assert stream.writes[1].endswith(cursor_up(3) + cursor_to(2) + show_cursor_escape)


def test_incremental_log_update_performs_surgical_updates():
    stream = FakeStream()
    log = LogUpdate(stream, incremental=True)

    log("Line 1\nLine 2\nLine 3\n")
    log("Line 1\nUpdated\nLine 3\n")

    second_write = stream.writes[1]
    assert cursor_next_line() in second_write
    assert "Updated" in second_write
    assert "Line 1" not in second_write
    assert "Line 3" not in second_write


def test_incremental_log_update_clears_extra_lines_when_output_shrinks():
    stream = FakeStream()
    log = LogUpdate(stream, incremental=True)

    log("Line 1\nLine 2\nLine 3\n")
    log("Line 1\n")

    assert erase_lines(2) in stream.writes[1]


def test_incremental_log_update_handles_no_trailing_newline_shrink():
    stream = FakeStream()
    log = LogUpdate(stream, incremental=True)

    log("A\nB")
    log("A")

    assert erase_lines(1) in stream.writes[1]
    assert not stream.writes[1].endswith("\n")


def test_incremental_log_update_handles_no_trailing_newline_grow():
    stream = FakeStream()
    log = LogUpdate(stream, incremental=True)

    log("A")
    log("A\nB\nC")

    assert "B" in stream.writes[1]
    assert "C" in stream.writes[1]


def test_incremental_log_update_grows_without_rewriting_unchanged_prefix():
    stream = FakeStream()
    log = LogUpdate(stream, incremental=True)

    log("Line 1\n")
    log("Line 1\nLine 2\nLine 3\n")

    second_write = stream.writes[1]
    assert cursor_next_line() in second_write
    assert "Line 2" in second_write
    assert "Line 3" in second_write
    assert "Line 1" not in second_write


def test_log_update_clear_returns_cursor_to_bottom_before_erasing_standard():
    stream = FakeStream()
    log = LogUpdate(stream)

    log.set_cursor_position((5, 0))
    log("Line 1\nLine 2\nLine 3\n")
    log.clear()

    clear_write = stream.writes[1]
    assert hide_cursor_escape in clear_write
    assert cursor_down(3) in clear_write
    assert erase_lines(4) in clear_write


def test_log_update_clear_returns_cursor_to_bottom_before_erasing_incremental():
    stream = FakeStream()
    log = LogUpdate(stream, incremental=True)

    log.set_cursor_position((5, 0))
    log("Line 1\nLine 2\nLine 3\n")
    log.clear()

    clear_write = stream.writes[1]
    assert hide_cursor_escape in clear_write
    assert cursor_down(3) in clear_write
    assert erase_lines(4) in clear_write


def test_incremental_log_update_renders_empty_string_as_full_clear():
    stream = FakeStream()
    log = LogUpdate(stream, incremental=True)

    log("Line 1\nLine 2\nLine 3\n")
    log("\n")

    assert stream.writes[1] == erase_lines(4) + "\n"


def test_incremental_log_update_shrinking_output_keeps_screen_tight():
    stream = FakeStream()
    log = LogUpdate(stream, incremental=True)

    log("Line 1\nLine 2\nLine 3\n")
    log("Line 1\nLine 2\n")
    log("Line 1\n")

    assert stream.writes[2] == erase_lines(2) + cursor_up(1) + cursor_next_line()


def test_incremental_log_update_clear_resets_state_for_fresh_render():
    stream = FakeStream()
    log = LogUpdate(stream, incremental=True)

    log("Line 1\nLine 2\nLine 3\n")
    log.clear()
    log("Line 1\n")

    assert stream.writes[-1] == erase_lines(0) + "Line 1\n"


def test_incremental_log_update_done_resets_state_for_fresh_render():
    stream = FakeStream()
    log = LogUpdate(stream, incremental=True)

    log("Line 1\nLine 2\nLine 3\n")
    log.done()
    log("Line 1\n")

    assert stream.writes[-1] == erase_lines(0) + "Line 1\n"


def test_incremental_log_update_sync_keeps_incremental_path():
    stream = FakeStream()
    log = LogUpdate(stream, incremental=True)

    log.sync("Line 1\nLine 2\nLine 3\n")
    assert stream.writes == []

    log("Line 1\nUpdated\nLine 3\n")
    assert len(stream.writes) == 1
    assert cursor_next_line() in stream.writes[0]
    assert "Updated" in stream.writes[0]
    assert "Line 1" not in stream.writes[0]
    assert "Line 3" not in stream.writes[0]


def test_log_update_sync_writes_cursor_suffix_when_cursor_dirty_standard():
    stream = FakeStream()
    log = LogUpdate(stream)

    log.set_cursor_position((5, 1))
    log.sync("Line 1\nLine 2\nLine 3\n")

    assert stream.writes == [cursor_up(2) + cursor_to(5) + show_cursor_escape]


def test_log_update_sync_writes_cursor_suffix_when_cursor_dirty_incremental():
    stream = FakeStream()
    log = LogUpdate(stream, incremental=True)

    log.set_cursor_position((5, 1))
    log.sync("Line 1\nLine 2\nLine 3\n")

    assert stream.writes == [cursor_up(2) + cursor_to(5) + show_cursor_escape]


def test_log_update_sync_hides_cursor_when_previous_render_showed_it():
    stream = FakeStream()
    log = LogUpdate(stream)

    log.set_cursor_position((5, 1))
    log("Line 1\nLine 2\nLine 3\n")
    log.sync("Fresh output\n")

    assert stream.writes[1] == hide_cursor_escape


def test_log_update_sync_resets_cursor_state_for_next_render():
    stream = FakeStream()
    log = LogUpdate(stream)

    log.set_cursor_position((5, 0))
    log("Line 1\nLine 2\nLine 3\n")
    log.sync("Fresh output\n")
    log("Updated output\n")

    after_sync_render = stream.writes[2]
    assert hide_cursor_escape not in after_sync_render
    assert cursor_down(3) not in after_sync_render


def test_incremental_log_update_trailing_to_no_trailing_transition():
    stream = FakeStream()
    log = LogUpdate(stream, incremental=True)

    log("A\nB\n")
    log("A\nB")

    second_write = stream.writes[1]
    assert cursor_next_line() in second_write
    assert not second_write.endswith("\n")


def test_incremental_log_update_no_trailing_to_no_trailing_update():
    stream = FakeStream()
    log = LogUpdate(stream, incremental=True)

    log("A\nB")
    log("A\nC")

    second_write = stream.writes[1]
    assert cursor_next_line() in second_write
    assert "C" in second_write
    assert not second_write.endswith("\n")


def test_incremental_log_update_no_trailing_unchanged_lines_do_not_overshoot_cursor():
    stream = FakeStream()
    log = LogUpdate(stream, incremental=True)

    log("A\nB")
    assert log("A\nB") is False
    assert len(stream.writes) == 1

    log("X\nB")
    third_write = stream.writes[1]
    assert "X" in third_write
    assert cursor_next_line() not in third_write


def test_log_update_sync_with_cursor_sets_cursor_was_shown_for_next_render_incremental():
    stream = FakeStream()
    log = LogUpdate(stream, incremental=True)

    log.set_cursor_position((5, 1))
    log.sync("Line 1\nLine 2\nLine 3\n")
    log("Updated\n")

    assert stream.writes[1].startswith(hide_cursor_escape)


def test_log_update_sync_without_cursor_does_not_write_standard():
    stream = FakeStream()
    log = LogUpdate(stream)

    log.sync("Line 1\nLine 2\nLine 3\n")
    assert stream.writes == []


def test_log_update_sync_without_cursor_does_not_write_incremental():
    stream = FakeStream()
    log = LogUpdate(stream, incremental=True)

    log.sync("Line 1\nLine 2\nLine 3\n")
    assert stream.writes == []
