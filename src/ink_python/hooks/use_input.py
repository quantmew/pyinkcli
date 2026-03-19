"""
useInput hook for ink-python.

Handles keyboard input from stdin.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    pass

from ink_python.hooks._runtime import useEffect
from ink_python.reconciler import discreteUpdates
from ink_python.hooks.use_stdin import useStdin
from ink_python.parse_keypress import parseKeypress


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
    stdin = useStdin()

    def manage_raw_mode():
        if not is_active:
            return None

        stdin.set_raw_mode(True)

        def cleanup():
            stdin.set_raw_mode(False)

        return cleanup

    useEffect(manage_raw_mode, (is_active,))

    def register_handler():
        if not is_active:
            return None

        def handle_data(data: str) -> None:
            char, key = _parse_keypress(data)
            discreteUpdates(lambda: handler(char, key))

        return stdin.on("input", handle_data)

    useEffect(register_handler, (is_active, handler))
def _parse_keypress(data: str) -> tuple[str, Key]:
    key = Key()
    if not data:
        return ("", key)

    parsed = parseKeypress(data)
    key.ctrl = parsed.ctrl
    key.shift = parsed.shift
    key.meta = parsed.meta or parsed.option
    key.super_key = parsed.super
    key.hyper = parsed.hyper
    key.caps_lock = parsed.capsLock
    key.num_lock = parsed.numLock
    key.event_type = parsed.eventType

    name = parsed.name
    if name == "up":
        key.up_arrow = True
    elif name == "down":
        key.down_arrow = True
    elif name == "left":
        key.left_arrow = True
    elif name == "right":
        key.right_arrow = True
    elif name == "pageup":
        key.page_up = True
    elif name == "pagedown":
        key.page_down = True
    elif name == "home":
        key.home = True
    elif name == "end":
        key.end = True
    elif name in {"return", "enter"}:
        key.return_pressed = True
    elif name == "escape":
        key.escape = True
    elif name == "tab":
        key.tab = True
    elif name == "backspace":
        key.backspace = True
    elif name == "delete":
        key.delete = True

    if len(data) == 1 and not any(
        [
            key.return_pressed,
            key.tab,
            key.backspace,
            key.escape,
            key.delete,
        ]
    ):
        return (data.lower() if key.ctrl else data, key)

    if parsed.name and len(parsed.name) == 1:
        return (parsed.name, key)

    return ("", key)


def _dispatch_input(data: str) -> None:
    """
    Dispatch input to all registered handlers.

    Args:
        data: Raw input data.
    """
    useStdin().emit("input", data)


def _clear_input_handlers() -> None:
    """Clear all input handlers."""
    useStdin().clear_event_handlers("input", "paste")
