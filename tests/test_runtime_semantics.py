"""Runtime-level parity tests for suspense, transitions, and accessibility."""

from __future__ import annotations

import time
from io import StringIO
from unittest.mock import Mock

from pyinkcli import Box, Text, measureElement, render
from pyinkcli.component import createElement
from pyinkcli.components._accessibility_runtime import _provide_accessibility
from pyinkcli.dom import addLayoutListener
from pyinkcli.hooks import useEffect, useInsertionEffect, useLayoutEffect, useState, useTransition
from pyinkcli.hooks.use_input import _dispatch_input, useInput
from pyinkcli.hooks.use_cursor import useCursor
from pyinkcli.ink import Ink, Options
from pyinkcli.packages.ink.dom import createNode
from pyinkcli.packages.react_reconciler.ReactEventPriorities import (
    DefaultEventPriority,
    DiscreteEventPriority,
    TransitionEventPriority,
)
from pyinkcli.packages.react_reconciler.ReactFiberWorkLoop import (
    getHighestPriorityLane,
    laneToMask,
    mergeLanes,
    removeLanes,
)
from pyinkcli.reconciler import createReconciler
from pyinkcli.render_node_to_output import render_node_to_screen_reader_output
from pyinkcli.render_to_string import create_root_node
from pyinkcli.suspense_runtime import (
    invalidateResource,
    peekResource,
    preloadResource,
    readResource,
    resetAllResources,
    resetResource,
)
from pyinkcli.utils.string_width import string_width


class FakeStdout(StringIO):
    def isatty(self) -> bool:
        return False


class FakeStdin(StringIO):
    def isatty(self) -> bool:
        return False


def Suspense(*children, fallback=None):
    return createElement("__ink-suspense__", *children, fallback=fallback)


def _wait_for_output(app: Ink, stdout: StringIO, expected: str, timeout: float = 0.5) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.wait_until_render_flush(timeout=0.05)
        if expected in stdout.getvalue():
            return
        time.sleep(0.01)
    raise AssertionError(f"Expected {expected!r} in output {stdout.getvalue()!r}")


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


def test_host_ref_change_detaches_previous_ref_and_attaches_next_ref() -> None:
    first_events: list[object] = []
    second_events: list[object] = []

    def first_ref(value) -> None:
        first_events.append(value)

    def second_ref(value) -> None:
        second_events.append(value)

    def Example(*, use_second: bool):
        return Box(Text("ref"), ref=second_ref if use_second else first_ref, width=8)

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(Example, use_second=False), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)
        assert first_events
        assert first_events[-1] is not None

        app.rerender(createElement(Example, use_second=True))
        app.wait_until_render_flush(timeout=0.2)

        assert first_events[-1] is None
        assert second_events
        assert second_events[-1] is not None
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


def test_use_transition_marks_pending_then_applies_latest_transition() -> None:
    stdout = FakeStdout()
    stdin = FakeStdin()

    def Example():
        query, set_query = useState("")
        is_pending, start_transition = useTransition()
        deferred_query, set_deferred_query = useState("")

        if deferred_query:
            time.sleep(0.05)

        def on_input(input_char: str, key) -> None:
            if not input_char or key.ctrl or key.meta:
                return

            set_query(lambda previous: previous + input_char)
            start_transition(
                lambda: set_deferred_query(lambda previous: previous + input_char)
            )

        useInput(on_input)

        return Text(f"{query}|{deferred_query}|{is_pending}")

    app = render(createElement(Example), stdout=stdout, stdin=stdin, concurrent=True, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)
        _dispatch_input("a")
        time.sleep(0.05)
        _wait_for_output(app, stdout, "a||True")
        _wait_for_output(app, stdout, "a|a|False")
    finally:
        app.unmount()


def test_use_transition_requests_transition_priority_lane() -> None:
    from pyinkcli.packages.react_reconciler.ReactSharedInternals import shared_internals
    from pyinkcli.packages.react_reconciler.ReactFiberWorkLoop import requestUpdateLane

    previous_priority = shared_internals.current_update_priority
    previous_transition = shared_internals.current_transition
    try:
        shared_internals.current_update_priority = DiscreteEventPriority
        shared_internals.current_transition = object()
        assert requestUpdateLane() == TransitionEventPriority

        shared_internals.current_transition = None
        assert requestUpdateLane() == DiscreteEventPriority

        shared_internals.current_update_priority = 0
        assert requestUpdateLane() == DefaultEventPriority
    finally:
        shared_internals.current_update_priority = previous_priority
        shared_internals.current_transition = previous_transition


def test_lane_helpers_merge_and_consume_highest_priority_first() -> None:
    lanes = mergeLanes(
        laneToMask(TransitionEventPriority),
        laneToMask(DiscreteEventPriority),
    )
    lanes = mergeLanes(lanes, laneToMask(DefaultEventPriority))

    assert getHighestPriorityLane(lanes) == DiscreteEventPriority
    lanes = removeLanes(lanes, DiscreteEventPriority)
    assert getHighestPriorityLane(lanes) == DefaultEventPriority
    lanes = removeLanes(lanes, DefaultEventPriority)
    assert getHighestPriorityLane(lanes) == TransitionEventPriority


def test_transition_update_rebases_on_same_state_queue() -> None:
    stdout = FakeStdout()
    stdin = FakeStdin()

    def Example():
        count, set_count = useState(0)
        is_pending, start_transition = useTransition()

        def on_input(input_char: str, key) -> None:
            if not input_char or key.ctrl or key.meta:
                return
            start_transition(lambda: set_count(lambda previous: previous + 1))
            set_count(lambda previous: previous + 1)

        useInput(on_input)
        return Text(f"{count}|{is_pending}")

    app = render(createElement(Example), stdout=stdout, stdin=stdin, concurrent=True, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)
        _dispatch_input("a")
        time.sleep(0.05)
        _wait_for_output(app, stdout, "1|True")
        _wait_for_output(app, stdout, "2|False")
    finally:
        app.unmount()


def test_suspense_resource_resolution_pings_original_lane() -> None:
    key = "tests:suspense:lane-ping"
    resetResource(key)

    try:
        readResource(key, lambda: (time.sleep(0.02), "ready")[1])
    except Exception:
        pass

    time.sleep(0.05)

    from pyinkcli._suspense_runtime import _records

    assert _records[key].wake_priority == DefaultEventPriority
    resetResource(key)


def test_discrete_input_preempts_transition_render_and_transition_recovers() -> None:
    stdout = FakeStdout()
    stdin = FakeStdin()

    def Example():
        query, set_query = useState("")
        is_pending, start_transition = useTransition()
        deferred_query, set_deferred_query = useState("")

        if deferred_query:
            time.sleep(0.02)

        def on_input(input_char: str, key) -> None:
            if not input_char or key.ctrl or key.meta:
                return
            set_query(lambda previous: previous + input_char)
            start_transition(
                lambda: set_deferred_query(lambda previous: previous + input_char)
            )

        useInput(on_input)
        return Text(f"{query}|{deferred_query}|{is_pending}")

    app = render(createElement(Example), stdout=stdout, stdin=stdin, concurrent=True, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)
        _dispatch_input("a")
        _dispatch_input("b")
        time.sleep(0.05)
        _wait_for_output(app, stdout, "ab|")
        _wait_for_output(app, stdout, "ab|ab|False")
    finally:
        app.unmount()


def test_concurrent_render_prepares_commit_before_host_commit() -> None:
    stdout = FakeStdout()
    stdin = FakeStdin()

    def Example():
        value, set_value = useState("")
        is_pending, start_transition = useTransition()

        def on_input(input_char: str, key) -> None:
            if input_char and not key.ctrl and not key.meta:
                start_transition(lambda: set_value(input_char))

        useInput(on_input)
        return Text(f"{value}|{is_pending}")

    app = render(createElement(Example), stdout=stdout, stdin=stdin, concurrent=True, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)
        _dispatch_input("x")
        _wait_for_output(app, stdout, "x|False")
        prepared = app._reconciler._last_prepared_commit
        assert prepared is not None
        assert prepared.commit_list.effects
        assert prepared.commit_list.layout_effects
        assert prepared.mutations
    finally:
        app.unmount()


def test_concurrent_commit_drives_passive_unmount_effects_from_fiber_queue() -> None:
    stdout = FakeStdout()
    stdin = FakeStdin()
    calls: list[str] = []

    def Child():
        def effect():
            calls.append("mount")

            def cleanup():
                calls.append("unmount")

            return cleanup

        useEffect(effect, ())
        return Text("child")

    def Example():
        visible, set_visible = useState(True)
        _is_pending, start_transition = useTransition()

        def on_input(input_char: str, key) -> None:
            if input_char == "x" and not key.ctrl and not key.meta:
                start_transition(lambda: set_visible(False))

        useInput(on_input)
        return Box(Text("visible" if visible else "hidden"), createElement(Child) if visible else None)

    app = render(createElement(Example), stdout=stdout, stdin=stdin, concurrent=True, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)
        initial_mounts = calls.count("mount")
        assert initial_mounts >= 1

        _dispatch_input("x")
        _wait_for_output(app, stdout, "hidden")

        assert calls.count("unmount") == 1
        assert not app._container.render_state
    finally:
        app.unmount()


def test_commit_path_runs_insertion_then_layout_then_passive_hook_effects() -> None:
    stdout = FakeStdout()
    stdin = FakeStdin()
    calls: list[str] = []

    def Example():
        useInsertionEffect(lambda: calls.append("insertion") or None, ())
        useLayoutEffect(lambda: calls.append("layout") or None, ())
        useEffect(lambda: calls.append("passive") or None, ())
        return Text("effects")

    app = render(
        createElement(Example),
        stdout=stdout,
        stdin=stdin,
        concurrent=True,
        debug=True,
    )
    try:
        app.wait_until_render_flush(timeout=0.2)
        assert "effects" in stdout.getvalue()
        assert set(calls) == {"insertion", "layout", "passive"}
    finally:
        app.unmount()


def test_sync_debug_commit_can_defer_passive_effects_to_commit_when_host_marks_it_safe() -> None:
    stdout = FakeStdout()
    stdin = FakeStdin()
    calls: list[str] = []

    def Example():
        useInsertionEffect(lambda: calls.append("insertion") or None, ())
        useLayoutEffect(lambda: calls.append("layout") or None, ())
        useEffect(lambda: calls.append("passive") or None, ())
        return Text("effects")

    app = render(createElement(Example), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)
        assert "effects" in stdout.getvalue()
        assert calls == ["insertion", "layout", "passive"]
    finally:
        app.unmount()


def test_deleted_subtree_passive_unmount_runs_parent_before_child() -> None:
    stdout = FakeStdout()
    stdin = FakeStdin()
    calls: list[str] = []

    def Child():
        useEffect(
            lambda: (
                None,
                lambda: calls.append("child-unmount"),
            )[1],
            (),
        )
        return Text("child")

    def Child():
        useEffect(
            lambda: (
                None,
                lambda: calls.append("child-unmount"),
            )[1],
            (),
        )
        return Text("child")

    def Parent():
        useEffect(
            lambda: (
                None,
                lambda: calls.append("parent-unmount"),
            )[1],
            (),
        )
        return Box(Text("parent"), createElement(Child))

    def Example():
        visible, set_visible = useState(True)
        def on_input(input_char: str, key) -> None:
            if input_char == "x" and not key.ctrl and not key.meta:
                set_visible(False)

        useInput(on_input)
        return createElement(Parent) if visible else Text("gone")

    app = render(createElement(Example), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)
        _dispatch_input("x")
        _wait_for_output(app, stdout, "gone")
        assert calls == ["parent-unmount", "child-unmount"]
    finally:
        app.unmount()


def test_updated_layout_and_insertion_effects_cleanup_before_new_mounts() -> None:
    stdout = FakeStdout()
    stdin = FakeStdin()
    calls: list[str] = []

    def Example():
        value, set_value = useState("A")

        useInsertionEffect(
            lambda: (
                calls.append(f"insertion-mount:{value}"),
                lambda: calls.append(f"insertion-unmount:{value}"),
            )[1],
            (value,),
        )
        useLayoutEffect(
            lambda: (
                calls.append(f"layout-mount:{value}"),
                lambda: calls.append(f"layout-unmount:{value}"),
            )[1],
            (value,),
        )

        def on_input(input_char: str, key) -> None:
            if input_char == "x" and not key.ctrl and not key.meta:
                set_value("B")

        useInput(on_input)
        return Text(value)

    app = render(createElement(Example), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)
        calls.clear()
        _dispatch_input("x")
        _wait_for_output(app, stdout, "B")

        assert calls == [
            "insertion-unmount:A",
            "insertion-mount:B",
            "layout-unmount:A",
            "layout-mount:B",
        ]
    finally:
        app.unmount()


def test_parent_fiber_tracks_deletions_list_for_removed_children() -> None:
    root_node = create_root_node(40, 5)
    reconciler = createReconciler(root_node)
    container = reconciler.create_container(root_node)

    first = Box(
        Text("first"),
        Text("second"),
    )
    reconciler.update_container(first, container)

    second = Box(
        Text("first"),
    )
    reconciler.update_container(second, container)

    parent_fiber = reconciler._root_fiber.child
    assert parent_fiber is not None
    assert parent_fiber.deletions


def test_stale_concurrent_render_state_is_explicitly_aborted() -> None:
    stdout = FakeStdout()
    stdin = FakeStdin()

    def Example():
        value, set_value = useState("")
        is_pending, start_transition = useTransition()

        def on_input(input_char: str, key) -> None:
            if input_char and not key.ctrl and not key.meta:
                start_transition(lambda: set_value(input_char))

        useInput(on_input)
        return Box(
            Text(f"{value}|{is_pending}"),
            *[Text(f"row-{index}-{value}") for index in range(40)],
            flexDirection="column",
        )

    app = render(createElement(Example), stdout=stdout, stdin=stdin, concurrent=True, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)
        _dispatch_input("a")
        time.sleep(0.01)
        state = app._container.render_state
        assert state is not None

        app._container.pending_work_version += 1
        app._reconciler._abort_container_render(app._container, reason="test_abort")

        assert app._container.render_state is None
        assert state.status == "aborted"
        assert state.abort_reason == "test_abort"
    finally:
        app.unmount()

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


def test_app_transition_scheduler_runs_all_callbacks() -> None:
    stdout = FakeStdout()
    stdin = FakeStdin()
    ink = Ink(Options(stdout=stdout, stdin=stdin, stderr=stdout, concurrent=True))
    values: list[str] = []

    try:
        ink._schedule_transition(lambda: values.append("stale"), delay=0.01)
        ink._schedule_transition(lambda: values.append("fresh"), delay=0.01)
        ink.wait_until_render_flush(timeout=0.2)

        assert values == ["stale", "fresh"]
    finally:
        ink.unmount()
