from __future__ import annotations

from pyinkcli.packages import react


def test_react_children_to_array_flattens_nested_children_and_assigns_keys() -> None:
    children = [
        react.createElement("ink-text", "a", key="explicit"),
        [
            react.createElement("ink-text", "b"),
            react.createElement("ink-text", "c", key="inner"),
        ],
    ]

    flattened = react.Children["toArray"](children)

    assert len(flattened) == 3
    assert [child.key for child in flattened] == [".$explicit", ".1:0", ".1:$inner"]


def test_react_children_map_preserves_computed_key_prefixes() -> None:
    children = [
        react.createElement("ink-text", "a", key="first"),
        react.createElement("ink-text", "b"),
    ]

    mapped = react.Children["map"](
        children,
        lambda child, _index: react.cloneElement(child, role="mapped"),
    )

    assert [child.key for child in mapped] == [".$first", ".1"]
    assert all(child.props["role"] == "mapped" for child in mapped)


def test_react_children_count_and_only_follow_react_style_contract() -> None:
    assert react.Children["count"](["a", ["b", None], react.createElement("ink-text", "c")]) == 3

    only_child = react.createElement("ink-text", "single")
    assert react.Children["only"](only_child) is only_child
