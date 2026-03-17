"""
useInput hook for ink-python.

Handles keyboard input from stdin.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class Key:
    """Information about a key press."""

    up_arrow: bool = False
    down_arrow: bool = False
    left_arrow: bool = False
    right_arrow: bool = False
    page_down: bool = False
    page_up: bool = False
    home: bool = False
    end: bool = False
    return_pressed: bool = False
    escape: bool = False
    ctrl: bool = False
    shift: bool = False
    tab: bool = False
    backspace: bool = False
    delete: bool = False
    meta: bool = False
    super_key: bool = False
    hyper: bool = False
    caps_lock: bool = False
    num_lock: bool = False
    event_type: Optional[str] = None  # 'press', 'repeat', 'release'

    def __repr__(self) -> str:
        parts = []
        if self.up_arrow:
            parts.append("↑")
        if self.down_arrow:
            parts.append("↓")
        if self.left_arrow:
            parts.append("←")
        if self.right_arrow:
            parts.append("→")
        if self.ctrl:
            parts.append("Ctrl")
        if self.shift:
            parts.append("Shift")
        if self.meta:
            parts.append("Meta")
        if self.tab:
            parts.append("Tab")
        if self.backspace:
            parts.append("Backspace")
        if self.delete:
            parts.append("Delete")
        if self.return_pressed:
            parts.append("Enter")
        if self.escape:
            parts.append("Esc")
        return f"Key({', '.join(parts)})"


# Input handlers registry
_input_handlers: list[Callable[[str, Key], None]] = []
_is_active: bool = True


def useInput(
    handler: Callable[[str, Key], None],
    *,
    is_active: bool = True,
) -> None:
    """
    Hook to handle keyboard input.

    Args:
        handler: Function called with (input, key) for each keypress.
        is_active: Whether the handler should receive input.

    Example:
        def MyComponent():
            def handle_input(input_char, key):
                if key.up_arrow:
                    # Handle up arrow
                    pass
                elif input_char == 'q':
                    # Quit on 'q'
                    pass

            useInput(handle_input)
            return Text("Press keys...")
    """
    global _input_handlers, _is_active

    # Store handler with its active state
    handler_entry = (handler, is_active)

    if handler_entry not in [(h, a) for h, a in _input_handlers]:
        _input_handlers.append(handler)


def use_input(
    handler: Callable[[str, Key], None],
    *,
    is_active: bool = True,
) -> None:
    """Alias for useInput."""
    return useInput(handler, is_active=is_active)


def _parse_keypress(data: str) -> tuple[str, Key]:
    """
    Parse raw input data into a character and Key object.

    Args:
        data: Raw input string.

    Returns:
        Tuple of (character, Key).
    """
    key = Key()

    if not data:
        return ("", key)

    # Handle ANSI escape sequences
    if data.startswith("\x1b"):
        if len(data) == 1:
            # Lone escape
            key.escape = True
            return ("", key)

        if data[1] == "[":
            # CSI sequence
            seq = data[2:] if len(data) > 2 else ""

            # Arrow keys
            if seq == "A":
                key.up_arrow = True
                return ("", key)
            elif seq == "B":
                key.down_arrow = True
                return ("", key)
            elif seq == "C":
                key.right_arrow = True
                return ("", key)
            elif seq == "D":
                key.left_arrow = True
                return ("", key)

            # Page up/down
            elif seq in ("5~", "5;5~"):
                key.page_up = True
                return ("", key)
            elif seq in ("6~", "6;5~"):
                key.page_down = True
                return ("", key)

            # Home/End
            elif seq in ("H", "1~", "7~"):
                key.home = True
                return ("", key)
            elif seq in ("F", "4~", "8~"):
                key.end = True
                return ("", key)

            # Delete
            elif seq in ("3~", "3;5~"):
                key.delete = True
                return ("", key)

            # Handle modified keys (e.g., ;5 for Ctrl)
            if ";" in seq:
                parts = seq.rsplit(";", 1)
                if len(parts) == 2:
                    modifier = parts[1][0] if parts[1] else ""
                    if modifier == "5":
                        key.ctrl = True
                    elif modifier == "2":
                        key.shift = True

    # Handle control characters
    if len(data) == 1:
        char = data[0]
        code = ord(char)

        if code == 13 or code == 10:  # Enter
            key.return_pressed = True
            return ("", key)
        elif code == 9:  # Tab
            key.tab = True
            return ("", key)
        elif code == 127 or code == 8:  # Backspace
            key.backspace = True
            return ("", key)
        elif code == 27:  # Escape
            key.escape = True
            return ("", key)
        elif code < 32:  # Ctrl + letter
            key.ctrl = True
            # Map to letter (1=a, 2=b, etc.)
            letter = chr(code + 96)
            return (letter, key)

    # Regular character
    if len(data) == 1:
        char = data
        if char.isupper():
            key.shift = True
        return (char, key)

    return (data, key)


def _dispatch_input(data: str) -> None:
    """
    Dispatch input to all registered handlers.

    Args:
        data: Raw input data.
    """
    global _input_handlers

    char, key = _parse_keypress(data)

    for handler in _input_handlers:
        try:
            handler(char, key)
        except Exception:
            pass  # Ignore handler errors


def _clear_input_handlers() -> None:
    """Clear all input handlers."""
    global _input_handlers
    _input_handlers.clear()
