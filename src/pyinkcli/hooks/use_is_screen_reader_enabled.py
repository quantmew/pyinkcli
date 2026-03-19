"""
useIsScreenReaderEnabled hook for pyinkcli.

This hook provides screen reader enabled state.
"""

from __future__ import annotations

from pyinkcli.components._accessibility_runtime import _is_screen_reader_enabled


def useIsScreenReaderEnabled() -> bool:
    """
    A React hook that returns whether a screen reader is enabled.

    This is useful when you want to render different output for screen readers.

    Returns:
        bool: Whether a screen reader is enabled for the current render tree.

    Example:
        >>> is_enabled = useIsScreenReaderEnabled()
        >>> if is_enabled:
        ...     # Render accessible output
        ...     pass
    """
    return _is_screen_reader_enabled()
