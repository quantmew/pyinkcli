"""Tests for hooks runtime behavior."""

import threading

from pyinkcli.components.CursorContext import _provide_cursor_context
from pyinkcli.hooks._runtime import (
    _batched_updates_runtime,
    _begin_component_render,
    _clear_hook_state,
    _consume_pending_rerender_priority,
    _discrete_updates_runtime,
    _end_component_render,
    _finish_hook_state,
    _reset_hook_state,
    _set_rerender_callback,
    _set_schedule_update_callback,
    useCallback,
    useEffect,
    useInsertionEffect,
    useLayoutEffect,
    useMemo,
    useRef,
    useState,
    useTransition,
)
from pyinkcli.hooks.use_cursor import useCursor
from pyinkcli.hooks.use_input import _clear_input_handlers, _dispatch_input, useInput
from pyinkcli.hooks.use_stdin import useStdin


def render_component(instance_id: str, component):
    _reset_hook_state()
    _begin_component_render(instance_id)
    try:
        result = component()
    finally:
        _end_component_render()
    _finish_hook_state()
    return result


def render_components(*items):
    _reset_hook_state()
    results = []
    for instance_id, component in items:
        _begin_component_render(instance_id)
        try:
            results.append(component())
        finally:
            _end_component_render()
    _finish_hook_state()
    return results


def teardown_function():
    _clear_hook_state()
    _set_rerender_callback(None)
    _set_schedule_update_callback(None)
    _clear_input_handlers()


def test_use_state_initial_value():
    value = render_component("counter", lambda: useState(5)[0])
    assert value == 5


def test_use_state_with_factory():
    value = render_component("factory", lambda: useState(lambda: 10)[0])
    assert value == 10


def test_use_state_persists_per_component_instance():
    def component():
        value, set_value = useState(0)
        if value == 0:
            set_value(1)
        return value

    first = render_component("component:a", component)
    second = render_component("component:a", component)
    other = render_component("component:b", component)

    assert first == 0
    assert second == 1
    assert other == 0


def test_use_ref_initial():
    ref = render_component("ref", lambda: useRef("hello"))
    assert ref.current == "hello"


def test_use_ref_mutable():
    ref = render_component("ref-mutable", lambda: useRef(0))
    ref.current = 5
    assert ref.current == 5


def test_use_memo():
    call_count = [0]

    def component():
        def factory():
            call_count[0] += 1
            return 42

        return useMemo(factory, (1, 2))

    result = render_component("memo", component)
    result2 = render_component("memo", component)
    assert result == 42
    assert result2 == 42
    assert call_count[0] == 1


def test_use_callback():
    def my_callback():
        return "hello"

    result = render_component("callback", lambda: useCallback(my_callback, (1,)))
    assert result() == "hello"


def test_use_transition_runs_callback_immediately_without_concurrent_app() -> None:
    calls: list[str] = []

    def component():
        is_pending, start_transition = useTransition()
        start_transition(lambda: calls.append("ran"))
        return is_pending

    first = render_component("transition-sync", component)

    assert first is False
    assert calls == ["ran"]


def test_use_effect_runs_after_render_and_cleans_up():
    calls: list[str] = []

    def component():
        dep, _ = useState(1)

        def effect():
            calls.append(f"run:{dep}")

            def cleanup():
                calls.append(f"cleanup:{dep}")

            return cleanup

        useEffect(effect, (dep,))
        return dep

    render_component("effect", component)
    render_component("effect", component)

    assert calls == ["run:1"]


def test_use_effect_cleanup_runs_on_unmount():
    calls: list[str] = []

    def component():
        def effect():
            calls.append("run")

            def cleanup():
                calls.append("cleanup")

            return cleanup

        useEffect(effect, ())

    render_component("effect-unmount", component)
    _clear_hook_state()

    assert calls == ["run", "cleanup"]


def test_use_effect_cleanup_runs_before_re_running_changed_deps():
    calls: list[str] = []

    def component():
        value, set_value = useState(0)

        def effect():
            calls.append(f"run:{value}")

            def cleanup():
                calls.append(f"cleanup:{value}")

            return cleanup

        useEffect(effect, (value,))
        if value == 0:
            set_value(1)
        return value

    first = render_component("effect-rerun", component)
    second = render_component("effect-rerun", component)

    assert first == 0
    assert second == 1
    assert calls == ["run:0", "cleanup:0", "run:1"]


def test_use_layout_and_insertion_effect_run_after_render_in_runtime_mode() -> None:
    calls: list[str] = []

    def component():
        def insertion():
            calls.append("insertion")
            return None

        def layout():
            calls.append("layout")
            return None

        useInsertionEffect(insertion, ())
        useLayoutEffect(layout, ())
        return "ok"

    assert render_component("effect-kinds", component) == "ok"
    assert calls == ["insertion", "layout"]


def test_use_input_keeps_single_subscription_across_rerenders_and_uses_latest_handler():
    calls: list[tuple[int, str]] = []

    def component():
        value, set_value = useState(0)

        def handler(input_char, key) -> None:
            calls.append((value, input_char))

        useInput(handler)

        if value == 0:
            set_value(1)

        return value

    first = render_component("use-input-stable-handler", component)
    second = render_component("use-input-stable-handler", component)

    assert first == 0
    assert second == 1
    assert useStdin().listener_count("input") == 1

    _dispatch_input("q")

    assert calls == [(1, "q")]


def test_use_state_setter_requests_rerender_each_time_it_updates() -> None:
    rerenders: list[str] = []

    def component():
        value, set_value = useState(0)
        if value == 0:
            set_value(1)
            set_value(2)
        return value

    _set_rerender_callback(lambda: rerenders.append("rerender"))
    render_component("rerender-count", component)

    assert rerenders == ["rerender", "rerender"]


def test_use_state_setter_auto_batches_same_tick_updates_outside_render() -> None:
    rerenders: list[str] = []
    setter_holder: list[object] = []
    rerendered = threading.Event()

    def component():
        value, set_value = useState(0)
        setter_holder[:] = [set_value]
        return value

    def on_rerender() -> None:
        rerenders.append("rerender")
        rerendered.set()

    _set_rerender_callback(on_rerender)
    render_component("auto-batched-rerender-count", component)

    set_value = setter_holder[0]
    set_value(1)
    set_value(2)

    assert rerendered.wait(0.2)
    assert rerenders == ["rerender"]
    assert render_component("auto-batched-rerender-count", component) == 2


def test_batch_updates_coalesces_multiple_state_updates_into_one_rerender() -> None:
    rerenders: list[str] = []

    def component():
        value, set_value = useState(0)
        if value == 0:
            _batched_updates_runtime(
                lambda: (
                    set_value(1),
                    set_value(2),
                )
            )
        return value

    _set_rerender_callback(lambda: rerenders.append("rerender"))
    render_component("batched-rerender-count", component)

    assert rerenders == ["rerender"]


def test_discrete_updates_coalesce_multiple_state_updates_into_one_rerender() -> None:
    rerenders: list[str] = []

    def component():
        value, set_value = useState(0)
        if value == 0:
            _discrete_updates_runtime(
                lambda: (
                    set_value(1),
                    set_value(2),
                )
            )
        return value

    _set_rerender_callback(lambda: rerenders.append("rerender"))
    render_component("discrete-rerender-count", component)

    assert rerenders == ["rerender"]


def test_schedule_update_callback_batches_non_discrete_updates_outside_render() -> None:
    setter_holder: list[object] = []
    scheduled: list[tuple[object, object]] = []
    flushed = threading.Event()

    def component():
        value, set_value = useState(0)
        setter_holder[:] = [set_value]
        return value

    def on_schedule(fiber, priority) -> None:
        scheduled.append((fiber, priority))
        flushed.set()

    _set_schedule_update_callback(on_schedule)
    render_component("scheduled-auto-batched", component)

    set_value = setter_holder[0]
    set_value(1)
    set_value(2)

    assert flushed.wait(0.2)
    assert len(scheduled) == 1


def test_render_phase_update_is_recorded_with_render_phase_priority() -> None:
    def component():
        value, set_value = useState(0)
        if value == 0:
            set_value(1)
        return value

    render_component("render-phase-priority", component)

    assert _consume_pending_rerender_priority() == "render_phase"


def test_hook_state_is_isolated_between_nested_component_instance_ids() -> None:
    def child(label: str):
        value, set_value = useState(0)
        if value == 0:
            set_value(1)
        return f"{label}:{value}"

    first = render_components(
        ("parent/child:a", lambda: child("a")),
        ("parent/child:b", lambda: child("b")),
    )

    second = render_components(
        ("parent/child:a", lambda: child("a")),
        ("parent/child:b", lambda: child("b")),
    )

    assert first == ["a:0", "b:0"]
    assert second == ["a:1", "b:1"]


def test_use_cursor_prefers_cursor_context_when_available() -> None:
    positions: list[object] = []

    class CursorContextValue:
        def setCursorPosition(self, position):
            positions.append(position)

    def component():
        cursor = useCursor()
        cursor.setCursorPosition({"x": 3, "y": 1})
        return None

    with _provide_cursor_context(CursorContextValue()):
        render_component("cursor-context", component)

    assert positions == [(3, 1)]


def test_hook_state_resets_after_component_unmount_and_remount() -> None:
    def child():
        value, set_value = useState(0)
        if value == 0:
            set_value(1)
        return value

    first = render_components(("branch/child", child))
    second = render_components(("branch/child", child))
    render_components()
    remounted = render_components(("branch/child", child))

    assert first == [0]
    assert second == [1]
    assert remounted == [0]
