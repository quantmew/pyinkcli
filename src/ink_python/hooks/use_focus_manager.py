"""
useFocusManager hook for ink-python.

This hook provides focus management functionality.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from ink_python.hooks.use_focus import focus_next, focus_prev, _focused_id, _focusable_ids


@dataclass
class UseFocusManagerOutput:
    """Output of useFocusManager hook."""

    enable_focus: Callable[[], None]
    disable_focus: Callable[[], None]
    focus_next: Callable[[], None]
    focus_previous: Callable[[], None]
    focus: Callable[[str], None]
    active_id: Optional[str]


def _enable_focus() -> None:
    """Enable focus management."""
    # Focus management is always enabled in the current implementation
    pass


def _disable_focus() -> None:
    """Disable focus management."""
    global _focused_id
    _focused_id = None


def _focus(id: str) -> None:
    """Focus element with given id."""
    global _focused_id
    if id in _focusable_ids:
        _focused_id = id


def use_focus_manager() -> UseFocusManagerOutput:
    """
    A React hook that returns methods to enable or disable focus management
    for all components or manually switch focus to the next or previous components.

    Returns:
        UseFocusManagerOutput: Object with focus management methods.

    Example:
        >>> focus_mgr = use_focus_manager()
        >>> focus_mgr.focus_next()
        >>> print(f"Focused: {focus_mgr.active_id}")
    """
    return UseFocusManagerOutput(
        enable_focus=_enable_focus,
        disable_focus=_disable_focus,
        focus_next=focus_next,
        focus_previous=focus_prev,
        focus=_focus,
        active_id=_focused_id,
    )


# Alias for camelCase preference
useFocusManager = use_focus_manager
