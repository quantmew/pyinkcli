"""
usePaste hook for ink-python.

Registers bracketed paste handlers on the shared stdin event bus.
"""

from __future__ import annotations

from typing import Callable, Optional

from ink_python.hooks._runtime import useEffect
from ink_python.hooks.use_stdin import useStdin


def usePaste(
    handler: Callable[[str], None],
    is_active: Optional[bool] = None,
) -> None:
    """
    Register a paste handler.
    """

    active = is_active is not False
    stdin = useStdin()

    def manage_input_modes():
        if not active:
            return None

        stdin.set_raw_mode(True)
        stdin.set_bracketed_paste_mode(True)

        def cleanup():
            stdin.set_raw_mode(False)
            stdin.set_bracketed_paste_mode(False)

        return cleanup

    useEffect(manage_input_modes, (active,))

    def subscribe():
        if not active:
            return None

        unsubscribe = stdin.on("paste", handler)
        return unsubscribe

    useEffect(subscribe, (active, handler))
