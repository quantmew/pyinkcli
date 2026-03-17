"""
useFocus hook for ink-python.

Manages focus state for focusable components.
"""

from __future__ import annotations

from typing import Optional, Tuple

from ink_python.hooks.state import useState, useEffect


# Global focus state
_focused_id: Optional[str] = None
_focusable_ids: list[str] = []


def useFocus(
    *,
    id: Optional[str] = None,
    auto_focus: bool = False,
    is_active: bool = True,
) -> Tuple[bool, callable]:
    """
    Hook to manage focus state.

    Args:
        id: Unique identifier for this focusable element.
        auto_focus: Whether to auto-focus this element.
        is_active: Whether this element can receive focus.

    Returns:
        Tuple of (is_focused, focus_function).
    """
    global _focused_id, _focusable_ids

    element_id = id or str(id(object()))
    is_focused, set_focused = useState(
        _focused_id == element_id or (auto_focus and _focused_id is None)
    )

    def focus():
        """Focus this element."""
        global _focused_id
        _focused_id = element_id
        set_focused(True)

    def blur():
        """Remove focus from this element."""
        global _focused_id
        if _focused_id == element_id:
            _focused_id = None
            set_focused(False)

    # Register this focusable element
    if is_active and element_id not in _focusable_ids:
        _focusable_ids.append(element_id)

    # Auto-focus logic
    if auto_focus and _focused_id is None and is_active:
        _focused_id = element_id

    # Check if focus changed
    if _focused_id == element_id and not is_focused:
        set_focused(True)
    elif _focused_id != element_id and is_focused:
        set_focused(False)

    return (is_focused and is_active, focus)


def use_focus(
    *,
    id: Optional[str] = None,
    auto_focus: bool = False,
    is_active: bool = True,
) -> Tuple[bool, callable]:
    """Alias for useFocus."""
    return useFocus(id=id, auto_focus=auto_focus, is_active=is_active)


def focus_next() -> None:
    """Move focus to the next focusable element."""
    global _focused_id, _focusable_ids

    if not _focusable_ids:
        return

    if _focused_id is None:
        _focused_id = _focusable_ids[0]
    else:
        try:
            index = _focusable_ids.index(_focused_id)
            next_index = (index + 1) % len(_focusable_ids)
            _focused_id = _focusable_ids[next_index]
        except ValueError:
            _focused_id = _focusable_ids[0]


def focus_prev() -> None:
    """Move focus to the previous focusable element."""
    global _focused_id, _focusable_ids

    if not _focusable_ids:
        return

    if _focused_id is None:
        _focused_id = _focusable_ids[-1]
    else:
        try:
            index = _focusable_ids.index(_focused_id)
            prev_index = (index - 1) % len(_focusable_ids)
            _focused_id = _focusable_ids[prev_index]
        except ValueError:
            _focused_id = _focusable_ids[-1]
