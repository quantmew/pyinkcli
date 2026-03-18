"""Runtime-level parity tests for suspense, transitions, and accessibility."""

from __future__ import annotations

import time
from io import StringIO

from ink_python import Box, Text, render
from ink_python.component import createElement
from ink_python.components._accessibility_runtime import _provide_accessibility
from ink_python.ink import Ink, Options
from ink_python.hooks.use_cursor import useCursor
from ink_python.hooks import useState
from ink_python.render_node_to_output import render_node_to_screen_reader_output
from ink_python.render_to_string import create_root_node
from ink_python.reconciler import createReconciler
from ink_python.utils.string_width import string_width
from ink_python.suspense_runtime import (
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
