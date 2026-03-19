from pyinkcli._yoga import DIRECTION_LTR
from pyinkcli.packages.react_dom import RenderResult, createRootNode, render


def test_create_root_node_sets_terminal_dimensions() -> None:
    root = createRootNode(columns=20, rows=5)
    assert root.yoga_node is not None

    root.yoga_node.calculate_layout(20, 5, DIRECTION_LTR)

    assert int(root.yoga_node.get_computed_width()) == 20
    assert int(root.yoga_node.get_computed_height()) == 5


def test_react_dom_render_returns_render_result() -> None:
    root = createRootNode(columns=10, rows=2)
    assert root.yoga_node is not None

    root.yoga_node.calculate_layout(10, 2, DIRECTION_LTR)

    result = render(root)

    assert isinstance(result, RenderResult)
    assert result.output.strip() == ""
    assert result.static_output == ""
