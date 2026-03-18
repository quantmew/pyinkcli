"""
useFocusManager hook for ink-python.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from ink_python.hooks._runtime import useEffect, useState
from ink_python.hooks.use_focus import _focus_runtime, focusNext, focusPrev


@dataclass
class _UseFocusManagerOutput:
    """Output of useFocusManager hook."""

    enable_focus: Callable[[], None]
    disable_focus: Callable[[], None]
    focus_next: Callable[[], None]
    focus_previous: Callable[[], None]
    focus: Callable[[str], None]
    active_id: Optional[str]


def useFocusManager() -> _UseFocusManagerOutput:
    """
    Hook exposing global focus controls.
    """

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
