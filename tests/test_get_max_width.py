"""Tests for JS-parity `getMaxWidth()` helper."""

from ink_python.get_max_width import getMaxWidth


class _FakeYogaNode:
    def get_computed_width(self) -> int:
        return 24

    def get_computed_padding(self, edge: int) -> int:
        return {
            0: 2,
            2: 3,
        }.get(edge, 0)

    def get_computed_border(self, edge: int) -> int:
        return {
            0: 1,
            2: 4,
        }.get(edge, 0)


def test_get_max_width_matches_js_formula() -> None:
    yoga_node = _FakeYogaNode()

    assert getMaxWidth(yoga_node) == 14
