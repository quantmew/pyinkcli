"""
useIsScreenReaderEnabled hook for ink-python.

This hook provides screen reader enabled state.
"""

from __future__ import annotations


def use_is_screen_reader_enabled() -> bool:
    """
    A React hook that returns whether a screen reader is enabled.

    This is useful when you want to render different output for screen readers.

    Returns:
        bool: Whether a screen reader is enabled. Currently always returns False
              as screen reader support is not yet implemented.

    Example:
        >>> is_enabled = use_is_screen_reader_enabled()
        >>> if is_enabled:
        ...     # Render accessible output
        ...     pass
    """
    # TODO: Implement actual screen reader detection
    return False


# Alias for camelCase preference
useIsScreenReaderEnabled = use_is_screen_reader_enabled
