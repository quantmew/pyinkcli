"""Runtime-level parity tests for suspense, transitions, and accessibility."""

from __future__ import annotations

import time
from io import StringIO
from unittest.mock import Mock

from pyinkcli import Box, Text, measureElement, render
from pyinkcli.component import createElement
from pyinkcli.dom import addLayoutListener
from pyinkcli.packages.ink.dom import createNode
from pyinkcli.components._accessibility_runtime import _provide_accessibility
from pyinkcli.ink import Ink, Options
from pyinkcli.hooks.use_cursor import useCursor
from pyinkcli.hooks import useState
from pyinkcli.render_node_to_output import render_node_to_screen_reader_output
from pyinkcli.render_to_string import create_root_node
from pyinkcli.reconciler import createReconciler
from pyinkcli.utils.string_width import string_width
from pyinkcli.suspense_runtime import (
    invalidateResource,
    peekResource,
    preloadResource,
    readResource,
    resetAllResources,
    resetResource,
)


class FakeStdout(StringIO):
    def isatty(self) -> bool:
        return False


class FakeStdin(StringIO):
    def isatty(self) -> bool:
        return False


def Suspense(*children, fallback=None):
    return createElement("__ink-suspense__", *children, fallback=fallback)


def test_screen_reader_checkbox_output_mentions_role_and_state() -> None:
    with _provide_accessibility(True):
        vnode = Box(
            Box(
                Text("[x]"),
                aria_role="checkbox",
                aria_state={"checked": True},
            ),
            Box(Text("Hidden"), aria_hidden=True),
            flexDirection="column",
        )

    root_node = create_root_node(40, 5)
    reconciler = createReconciler(root_node)
    container = reconciler.create_container(root_node)
    reconciler.update_container(vnode, container)

    output = render_node_to_screen_reader_output(root_node)

    assert "checkbox:" in output
    assert "checked" in output
    assert "Hidden" not in output


def test_screen_reader_output_matches_js_role_and_state_format() -> None:
    with _provide_accessibility(True):
        vnode = Box(
            Text("Select a color:"),
            Box(
                Text("Green"),
                aria_label="2. Green",
                aria_role="listitem",
                aria_state={"selected": True},
            ),
            aria_role="list",
            flexDirection="column",
        )

    root_node = create_root_node(40, 5)
    reconciler = createReconciler(root_node)
    container = reconciler.create_container(root_node)
    reconciler.update_container(vnode, container)

    output = render_node_to_screen_reader_output(root_node)

    assert output == "list: Select a color:\nlistitem: (selected) 2. Green"


def test_reconciler_runs_layout_callback_before_emitting_layout_listeners() -> None:
    root_node = create_root_node(40, 5)
    events: list[str] = []

    def on_compute_layout() -> None:
        events.append("layout")

    root_node.onComputeLayout = on_compute_layout
    addLayoutListener(root_node, lambda: events.append("listener"))

    reconciler = createReconciler(root_node)
    container = reconciler.create_container(root_node)
    reconciler.update_container(Box(Text("Hello")), container)

    assert events == ["layout", "listener"]


def test_measure_element_returns_zero_before_layout() -> None:
    node = createNode("ink-box")
    dimensions = measureElement(node)

    assert dimensions.width == 0
    assert dimensions.height == 0


def test_callback_ref_measurement_matches_ink_progress_bar_pattern() -> None:
    def Example():
        width, set_width = useState(0)
        ref, set_ref = useState(None)

        if ref is not None:
            dimensions = measureElement(ref)
            if dimensions.width != width:
                set_width(dimensions.width)

        return Box(Text(f"Width: {width}"), ref=set_ref, width=12)

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(Example), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)
        assert "Width: 12" in stdout.getvalue()
    finally:
        app.unmount()


def test_ink_wires_root_callbacks_for_commit_flow() -> None:
    stdout = FakeStdout()
    stdin = FakeStdin()
    app = Ink(Options(stdout=stdout, stdin=stdin, stderr=stdout, debug=True))
    try:
        assert callable(app._root_node.onComputeLayout)
        assert callable(app._root_node.onRender)
        assert callable(app._root_node.onImmediateRender)
    finally:
        app.unmount()


def test_request_commit_render_uses_root_callbacks() -> None:
    stdout = FakeStdout()
    stdin = FakeStdin()
    app = Ink(Options(stdout=stdout, stdin=stdin, stderr=stdout, debug=True))
    try:
        on_render = Mock()
        on_immediate_render = Mock()
        app._root_node.onRender = on_render
        app._root_node.onImmediateRender = on_immediate_render

        app._request_commit_render("default", immediate=False)
        app._request_commit_render("discrete", immediate=True)

        on_render.assert_called_once_with()
        on_immediate_render.assert_called_once_with()
    finally:
        app.unmount()


def test_suspense_renders_fallback_then_resolved_content() -> None:
    stdout = FakeStdout()
    stdin = FakeStdin()
    key = "tests:suspense:message"

    def read_message() -> str:
        return readResource(
            key,
            lambda: (time.sleep(0.05), "Hello World")[1],
        )

    def Example():
        return Text(read_message())

    vnode = createElement(
        Suspense,
        createElement(Example),
        fallback=createElement(Text, "Loading..."),
    )

    resetResource(key)
    app = render(vnode, stdout=stdout, stdin=stdin, concurrent=True, debug=True)
    try:
        time.sleep(0.01)
        app.wait_until_render_flush(timeout=0.2)
        assert "Loading..." in stdout.getvalue()

        time.sleep(0.08)
        app.wait_until_render_flush(timeout=0.2)
        assert "Hello World" in stdout.getvalue()
    finally:
        app.unmount()
        resetResource(key)


def test_suspense_runtime_supports_preload_peek_and_invalidate() -> None:
    key = "tests:suspense:preload"

    invalidateResource(key)
    assert peekResource(key) is None

    preloadResource(key, lambda: (time.sleep(0.02), "prefetched")[1])
    time.sleep(0.05)
    assert peekResource(key) == "prefetched"

    invalidateResource(key)
    assert peekResource(key) is None

    resetAllResources()

def test_use_cursor_normalizes_negative_positions() -> None:
    def Example():
        cursor = useCursor()
        cursor.setCursorPosition({"x": -4, "y": -2})
        return Text("cursor")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(Example), stdout=stdout, stdin=stdin, debug=True)
    try:
        assert app._log._cursor_position == (0, 0)
    finally:
        app.unmount()


def test_cursor_ime_style_position_uses_string_width_for_cjk_input() -> None:
    def Example():
        cursor = useCursor()
        text = "中文"
        prompt = "> "
        cursor.setCursorPosition({"x": string_width(prompt + text), "y": 1})
        return Box(
            Text("Type Korean (Ctrl+C to exit):"),
            Text(f"{prompt}{text}"),
            flexDirection="column",
        )

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(Example), stdout=stdout, stdin=stdin, debug=True)
    try:
        assert app._log._cursor_position == (6, 1)
    finally:
        app.unmount()


def test_app_transition_scheduler_commits_only_latest_callback() -> None:
    stdout = FakeStdout()
    stdin = FakeStdin()
    ink = Ink(Options(stdout=stdout, stdin=stdin, stderr=stdout, concurrent=True))
    values: list[str] = []

    try:
        ink._schedule_transition(lambda: values.append("stale"), delay=0.01)
        ink._schedule_transition(lambda: values.append("fresh"), delay=0.01)
        ink.wait_until_render_flush(timeout=0.2)

        assert values == ["fresh"]
    finally:
        ink.unmount()
