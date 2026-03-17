"""
useCursor hook for ink-python.

This hook provides cursor visibility control.
"""

from __future__ import annotations

from typing import Callable

from ink_python.hooks.use_app import use_app
from ink_python.utils.ansi_escapes import cursor_show, cursor_hide


# Global cursor visibility state
_cursor_visible: bool = True
_cursor_handlers: list[Callable[[bool], None]] = []


def _set_cursor_visibility(visible: bool) -> None:
    """Set global cursor visibility."""
    global _cursor_visible
    _cursor_visible = visible

    # Notify all registered handlers
    for handler in _cursor_handlers:
        try:
            handler(visible)
        except Exception:
            pass


def use_cursor(visible: bool) -> None:
    """
    A React hook that controls cursor visibility.

    Args:
        visible: Whether the cursor should be visible.

    Example:
        >>> use_cursor(False)  # Hide cursor
        >>> use_cursor(True)   # Show cursor
    """
    global _cursor_handlers

    def update_cursor(is_visible: bool) -> None:
        """Update cursor visibility."""
        app = use_app()
        if is_visible:
            app.write(cursor_show())
        else:
            app.write(cursor_hide())

    # Register handler
    if update_cursor not in _cursor_handlers:
        _cursor_handlers.append(update_cursor)

    # Apply immediately
    _set_cursor_visibility(visible)


# Alias for camelCase preference
useCursor = use_cursor


def _clear_cursor_handlers() -> None:
    """Clear all cursor handlers."""
    global _cursor_handlers
    _cursor_handlers.clear()
