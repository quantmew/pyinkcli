"""Tests for focus hooks runtime."""

from ink_python.hooks.state import (
    _begin_component_render,
    _clear_hook_state,
    _end_component_render,
    _finish_hook_state,
    _reset_hook_state,
    _set_rerender_callback,
)
from ink_python.hooks.use_focus import _focus_runtime, useFocus
from ink_python.hooks.use_focus_manager import useFocusManager


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
    _focus_runtime.entries.clear()
    _focus_runtime.active_id = None
    _focus_runtime.enabled = True
    _focus_runtime.listeners.clear()


def test_use_focus_auto_focuses_first_active_entry():
    render_components(
        ("focus:a", lambda: useFocus(id="a", auto_focus=True)),
        ("focus:b", lambda: useFocus(id="b")),
    )
    first, second = render_components(
        ("focus:a", lambda: useFocus(id="a", auto_focus=True)),
        ("focus:b", lambda: useFocus(id="b")),
    )

    assert first[0] is True
    assert second[0] is False
    assert _focus_runtime.active_id == "a"


def test_focus_manager_moves_focus_between_registered_entries():
    _, _, manager = render_components(
        ("focus:a", lambda: useFocus(id="a", auto_focus=True)),
        ("focus:b", lambda: useFocus(id="b")),
        ("focus-manager", useFocusManager),
    )

    manager.focus_next()
    assert _focus_runtime.active_id == "b"

    manager.focus_previous()
    assert _focus_runtime.active_id == "a"


def test_focus_manager_can_disable_focus():
    _, manager = render_components(
        ("focus:a", lambda: useFocus(id="a", auto_focus=True)),
        ("focus-manager", useFocusManager),
    )

    manager.disable_focus()
    assert _focus_runtime.enabled is False
    assert _focus_runtime.active_id is None
