"""
useFocusManager hook for pyinkcli.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pyinkcli.components.FocusContext import _get_focus_context
from pyinkcli.hooks._runtime import useEffect, useState
from pyinkcli.hooks.use_focus import _focus_runtime, focusNext, focusPrev


@dataclass
class _UseFocusManagerOutput:
    """Output of useFocusManager hook."""

    enable_focus: Callable[[], None]
    disable_focus: Callable[[], None]
    focus_next: Callable[[], None]
    focus_previous: Callable[[], None]
    focus: Callable[[str], None]
    active_id: str | None


def useFocusManager() -> _UseFocusManagerOutput:
    """
    Hook exposing global focus controls.
    """

    focus_context = _get_focus_context()
    if focus_context is not None:
        return _UseFocusManagerOutput(
            enable_focus=focus_context.enableFocus,
            disable_focus=focus_context.disableFocus,
            focus_next=focus_context.focusNext,
            focus_previous=focus_context.focusPrevious,
            focus=focus_context.focus,
            active_id=focus_context.active_id,
        )

    _, set_version = useState(0)

    def force_update() -> None:
        set_version(lambda value: value + 1)

    def subscribe():
        return _focus_runtime.subscribe(force_update)

    useEffect(subscribe, ())

    return _UseFocusManagerOutput(
        enable_focus=_focus_runtime.enable_focus,
        disable_focus=_focus_runtime.disable_focus,
        focus_next=focusNext,
        focus_previous=focusPrev,
        focus=_focus_runtime.focus,
        active_id=_focus_runtime.active_id,
    )
