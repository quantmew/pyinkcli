"""Tests for incremental reconciler behavior."""

from ink_python.component import createElement
from ink_python.dom import createNode
from ink_python.reconciler import createReconciler


def test_reconciler_reuses_host_nodes_on_update():
    root = createNode("ink-root")
    reconciler = createReconciler(root)
    container = reconciler.create_container(root)

    first_tree = createElement(
        "ink-box",
        createElement("ink-text", "hello"),
        flexDirection="column",
    )
    reconciler.update_container(first_tree, container)

    box_node = root.child_nodes[0]
    text_node = box_node.child_nodes[0]
    text_leaf = text_node.child_nodes[0]

    second_tree = createElement(
        "ink-box",
        createElement("ink-text", "world"),
        flexDirection="column",
    )
    reconciler.update_container(second_tree, container)

    assert root.child_nodes[0] is box_node
    assert box_node.child_nodes[0] is text_node
    assert text_node.child_nodes[0] is text_leaf
    assert text_leaf.node_value == "world"


def test_reconciler_trims_removed_children_without_replacing_survivors():
    root = createNode("ink-root")
    reconciler = createReconciler(root)
    container = reconciler.create_container(root)

    first_tree = createElement(
        "ink-box",
        createElement("ink-text", "first"),
        createElement("ink-text", "second"),
    )
    reconciler.update_container(first_tree, container)

    box_node = root.child_nodes[0]
    first_child = box_node.child_nodes[0]

    second_tree = createElement(
        "ink-box",
        createElement("ink-text", "first"),
    )
    reconciler.update_container(second_tree, container)

    assert root.child_nodes[0] is box_node
    assert len(box_node.child_nodes) == 1
    assert box_node.child_nodes[0] is first_child


def test_reconciler_reorders_keyed_children_without_recreating_them():
    root = createNode("ink-root")
    reconciler = createReconciler(root)
    container = reconciler.create_container(root)

    first_tree = createElement(
        "ink-box",
        createElement("ink-text", "first", key="a"),
        createElement("ink-text", "second", key="b"),
    )
    reconciler.update_container(first_tree, container)

    box_node = root.child_nodes[0]
    first_child = box_node.child_nodes[0]
    second_child = box_node.child_nodes[1]

    second_tree = createElement(
        "ink-box",
        createElement("ink-text", "second", key="b"),
        createElement("ink-text", "first", key="a"),
    )
    reconciler.update_container(second_tree, container)

    assert box_node.child_nodes[0] is second_child
    assert box_node.child_nodes[1] is first_child
