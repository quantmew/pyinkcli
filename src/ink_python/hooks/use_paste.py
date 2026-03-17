"""
usePaste hook for ink-python.

This hook provides paste handling functionality.
"""

from __future__ import annotations

from typing import Callable, Optional

from ink_python.hooks.use_stdin import use_stdin
from ink_python.hooks.use_input import Key


def use_paste(
    handler: Callable[[str], None],
    is_active: Optional[bool] = None,
) -> None:
    """
    A React hook that calls `handler` whenever the user pastes text in the terminal.

    Bracketed paste mode is automatically enabled while the hook is active,
    so pasted text arrives as a single string rather than being misinterpreted
    as individual key presses.

    `use_paste` and `use_input` can be used together in the same component.
    They operate on separate event channels, so paste content is never
    forwarded to `use_input` handlers when `use_paste` is active.

    Args:
        handler: Callback function that receives the pasted text.
        is_active: Enable or disable the paste handler. Defaults to True.

    Example:
        >>> def handle_paste(text):
        ...     print(f"Pasted: {text}")
        >>> use_paste(handle_paste)

        >>> # With use_input together
        >>> use_input(lambda input, key: print(f"Typed: {input}"))
        >>> use_paste(lambda text: print(f"Pasted: {text}"))
    """
    stdin = use_stdin()

    if is_active is False:
        return

    # Enable bracketed paste mode
    stdin.set_bracketed_paste_mode(True)

    # Register paste handler
    stdin.on("paste", handler)

    # Cleanup on unmount
    def cleanup():
        stdin.set_bracketed_paste_mode(False)
        stdin.off("paste", handler)

    # Note: In a real React hook, we'd use useEffect here
    # For now, this is a simplified version


# Alias for camelCase preference
usePaste = use_paste
