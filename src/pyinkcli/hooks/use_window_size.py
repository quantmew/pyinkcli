"""
useWindowSize hook for pyinkcli.

Provides terminal window size information.
"""

from __future__ import annotations

from pyinkcli.hooks._runtime import useEffect, useState
from pyinkcli.hooks.use_stdout import useStdout


def useWindowSize() -> tuple[int, int]:
    """
    Hook to get the terminal window size.

    Returns:
        Tuple of (width, height) in columns and rows.
    """
    stdout = useStdout()
    size, set_size = useState((stdout.columns, stdout.rows))

    def setup():
        def on_resize():
            set_size((stdout.columns, stdout.rows))

        return stdout.on_resize(on_resize)

    useEffect(setup, (stdout,))
    return size
