"""Tests for incremental reconciler behavior."""

import time

from ink_python.component import createElement
from ink_python.dom import createNode
from ink_python.hooks._runtime import useState
from ink_python.reconciler import (
    batchedUpdates,
    consumePendingRerenderPriority,
    createReconciler,
    discreteUpdates,
)


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


def test_concurrent_container_coalesces_to_latest_tree() -> None:
    root = createNode("ink-root")
    reconciler = createReconciler(root)
    container = reconciler.create_container(root, tag=1)

    reconciler.update_container(createElement("ink-text", "first"), container)
    reconciler.update_container(createElement("ink-text", "second"), container)

    deadline = time.time() + 0.5
    while time.time() < deadline:
        if root.child_nodes:
            text_node = root.child_nodes[0]
            if text_node.child_nodes and text_node.child_nodes[0].node_value == "second":
                break
        time.sleep(0.01)

    text_node = root.child_nodes[0]
    assert text_node.child_nodes[0].node_value == "second"


def test_reconciler_module_update_helpers_expose_batched_and_discrete_surfaces() -> None:
    setter_holder: list[object] = []

    def component():
        value, set_value = useState(0)
        setter_holder[:] = [set_value]
        return createElement("ink-text", str(value))

    root = createNode("ink-root")
    reconciler = createReconciler(root)
    container = reconciler.create_container(root)
    reconciler.update_container_sync(createElement(component), container)
    reconciler.flush_sync_work(container)

    set_value = setter_holder[0]

    batchedUpdates(lambda: (set_value(1), set_value(2)))
    assert consumePendingRerenderPriority() == "default"

    discreteUpdates(lambda: set_value(3))
    assert consumePendingRerenderPriority() == "discrete"


def test_reconciler_commit_handlers_receive_normal_and_immediate_commits() -> None:
    root = createNode("ink-root")
    reconciler = createReconciler(root)
    container = reconciler.create_container(root)
    calls: list[str] = []
    reconciler.set_commit_handlers(
        on_commit=lambda: calls.append("normal"),
        on_immediate_commit=lambda: calls.append("immediate"),
    )

    reconciler.update_container_sync(createElement("ink-text", "hello"), container)
    reconciler.flush_sync_work(container)

    reconciler.update_container_sync(
        createElement("ink-box", createElement("ink-text", "static"), internal_static=True),
        container,
    )
    reconciler.flush_sync_work(container)

    assert calls == ["normal", "immediate"]
