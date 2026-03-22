"""Tests for incremental reconciler behavior."""

import time

from pyinkcli.component import component, createElement
from pyinkcli.dom import createNode
from pyinkcli.hooks._runtime import useEffect, useRef, useState
from pyinkcli.packages import react
from pyinkcli import render
from pyinkcli.reconciler import (
    batchedUpdates,
    consumePendingRerenderPriority,
    createReconciler,
    discreteUpdates,
)
from pyinkcli.packages.react_router import MemoryRouter, useLocation


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

    box_node = root.childNodes[0]
    text_node = box_node.childNodes[0]
    text_leaf = text_node.childNodes[0]

    second_tree = createElement(
        "ink-box",
        createElement("ink-text", "world"),
        flexDirection="column",
    )
    reconciler.update_container(second_tree, container)

    assert root.childNodes[0] is box_node
    assert box_node.childNodes[0] is text_node
    assert text_node.childNodes[0] is text_leaf
    assert text_leaf.nodeValue == "world"


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

    box_node = root.childNodes[0]
    first_child = box_node.childNodes[0]

    second_tree = createElement(
        "ink-box",
        createElement("ink-text", "first"),
    )
    reconciler.update_container(second_tree, container)

    assert root.childNodes[0] is box_node
    assert len(box_node.childNodes) == 1
    assert box_node.childNodes[0] is first_child


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

    box_node = root.childNodes[0]
    first_child = box_node.childNodes[0]
    second_child = box_node.childNodes[1]

    second_tree = createElement(
        "ink-box",
        createElement("ink-text", "second", key="b"),
        createElement("ink-text", "first", key="a"),
    )
    reconciler.update_container(second_tree, container)

    assert box_node.childNodes[0] is second_child
    assert box_node.childNodes[1] is first_child


def test_concurrent_container_coalesces_to_latest_tree() -> None:
    root = createNode("ink-root")
    reconciler = createReconciler(root)
    container = reconciler.create_container(root, tag=1)

    reconciler.update_container(createElement("ink-text", "first"), container)
    reconciler.update_container(createElement("ink-text", "second"), container)

    deadline = time.time() + 0.5
    while time.time() < deadline:
        if root.childNodes:
            text_node = root.childNodes[0]
            if text_node.childNodes and text_node.childNodes[0].nodeValue == "second":
                break
        time.sleep(0.01)

    text_node = root.childNodes[0]
    assert text_node.childNodes[0].nodeValue == "second"


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


def test_begin_work_rerenders_context_dependent_subtree_when_provider_value_changes() -> None:
    render_count = 0
    value_context = react.createContext("fallback")

    def Reader():
        nonlocal render_count
        render_count += 1
        return createElement("ink-text", react.useContext(value_context))

    root = createNode("ink-root")
    reconciler = createReconciler(root)
    container = reconciler.create_container(root)

    reconciler.update_container_sync(
        createElement(value_context.Provider, createElement(Reader), value="first"),
        container,
    )
    reconciler.update_container_sync(
        createElement(value_context.Provider, createElement(Reader), value="second"),
        container,
    )

    assert render_count == 2
    assert root.childNodes[0].childNodes[0].nodeValue == "second"


def test_begin_work_bails_out_leaf_function_component_without_hooks() -> None:
    render_count = 0

    def Child(label: str):
        nonlocal render_count
        render_count += 1
        return createElement("ink-text", label)

    def App(label: str):
        return createElement("ink-box", createElement(Child, label=label))

    root = createNode("ink-root")
    reconciler = createReconciler(root)
    container = reconciler.create_container(root)

    reconciler.update_container_sync(createElement(App, label="same"), container)
    reconciler.update_container_sync(createElement(App, label="same"), container)

    assert render_count == 1


def test_begin_work_bails_out_function_component_with_ref_and_stable_effect_deps() -> None:
    render_count = 0

    def Child(label: str):
        nonlocal render_count
        render_count += 1
        ref = useRef("stable")
        assert ref.current == "stable"
        useEffect(lambda: None, (label,))
        return createElement("ink-text", label)

    root = createNode("ink-root")
    reconciler = createReconciler(root)
    container = reconciler.create_container(root)

    reconciler.update_container_sync(createElement(Child, label="same"), container)
    reconciler.update_container_sync(createElement(Child, label="same"), container)

    assert render_count == 1


def test_begin_work_does_not_bail_out_function_component_with_effect_without_deps() -> None:
    render_count = 0

    def Child(label: str):
        nonlocal render_count
        render_count += 1
        useEffect(lambda: None)
        return createElement("ink-text", label)

    root = createNode("ink-root")
    reconciler = createReconciler(root)
    container = reconciler.create_container(root)

    reconciler.update_container_sync(createElement(Child, label="same"), container)
    reconciler.update_container_sync(createElement(Child, label="same"), container)

    assert render_count == 2


def test_begin_work_bails_out_internal_router_like_wrapper_with_context_read_only() -> None:
    render_count = 0

    def RouterReader():
        nonlocal render_count
        render_count += 1
        return createElement("ink-text", useLocation().pathname)

    RouterReader.__module__ = "pyinkcli.tests.router_like"
    RouterReader.__ink_runtime_sources__ = ("router.location",)

    root = createNode("ink-root")
    reconciler = createReconciler(root)
    container = reconciler.create_container(root)
    tree = createElement(MemoryRouter, createElement(RouterReader), initialEntries=["/same"])

    reconciler.update_container_sync(tree, container)
    reconciler.update_container_sync(tree, container)

    assert render_count == 1


def test_begin_work_bails_out_internal_control_component_with_stable_effects() -> None:
    render_count = 0

    def CursorController(label: str):
        nonlocal render_count
        render_count += 1
        ref = useRef("stable")
        assert ref.current == "stable"
        useEffect(lambda: None, (label,))
        return createElement("ink-text", label)

    CursorController.__module__ = "pyinkcli.tests.internal_control"
    CursorController.__ink_runtime_sources__ = ("cursor",)

    root = createNode("ink-root")
    reconciler = createReconciler(root)
    container = reconciler.create_container(root)

    reconciler.update_container_sync(createElement(CursorController, label="same"), container)
    reconciler.update_container_sync(createElement(CursorController, label="same"), container)

    assert render_count == 1


def test_begin_work_distinguishes_router_location_and_navigation_runtime_sources() -> None:
    render_count = 0

    def RouterLocationReader():
        nonlocal render_count
        render_count += 1
        return createElement("ink-text", useLocation().pathname)

    RouterLocationReader.__module__ = "pyinkcli.tests.router_location_only"
    RouterLocationReader.__ink_runtime_sources__ = ("router.location",)

    root = createNode("ink-root")
    reconciler = createReconciler(root)
    container = reconciler.create_container(root)
    tree = createElement(MemoryRouter, createElement(RouterLocationReader), initialEntries=["/same"])

    reconciler.update_container_sync(tree, container)
    reconciler.update_container_sync(tree, container)

    assert render_count == 1


def test_begin_work_does_not_bail_out_internal_component_with_unsupported_runtime_source() -> None:
    render_count = 0

    def ImperativeWrapper(label: str):
        nonlocal render_count
        render_count += 1
        useRef("stable")
        return createElement("ink-text", label)

    ImperativeWrapper.__module__ = "pyinkcli.tests.imperative_like"
    ImperativeWrapper.__ink_runtime_sources__ = ("imperative_render",)

    root = createNode("ink-root")
    reconciler = createReconciler(root)
    container = reconciler.create_container(root)

    reconciler.update_container_sync(createElement(ImperativeWrapper, label="same"), container)
    reconciler.update_container_sync(createElement(ImperativeWrapper, label="same"), container)

    assert render_count == 2


def test_imperative_component_rerender_invalidates_runtime_source_dependency() -> None:
    class _Stdout:
        def __init__(self) -> None:
            self._parts: list[str] = []

        def isatty(self) -> bool:
            return False

        def write(self, value: str) -> int:
            self._parts.append(value)
            return len(value)

        def flush(self) -> None:
            return None

        def getvalue(self) -> str:
            return "".join(self._parts)

    class _Stdin:
        def isatty(self) -> bool:
            return False

    label = "first"
    render_count = 0

    @component
    def Example():
        nonlocal render_count
        render_count += 1
        return createElement("ink-text", label)

    stdout = _Stdout()
    stdin = _Stdin()
    app = render(Example, stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)
        label = "second"
        app.rerender(Example)
        app.wait_until_render_flush(timeout=0.2)
    finally:
        app.unmount()

    assert render_count == 2
    assert "second" in stdout.getvalue()
