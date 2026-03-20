"""
usePaste hook for pyinkcli.

Registers bracketed paste handlers on the shared stdin event bus.
"""

from __future__ import annotations

from collections.abc import Callable

from pyinkcli.hooks._runtime import useEffect
from pyinkcli.hooks.use_stdin import useStdin
from pyinkcli.packages.react_reconciler.ReactFiberReconciler import discreteUpdates


def usePaste(
    handler: Callable[[str], None],
    is_active: bool | None = None,
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

        unsubscribe = stdin.on(
            "paste",
            lambda text: discreteUpdates(lambda: handler(text)),
        )
        return unsubscribe

    useEffect(subscribe, (active, handler))
