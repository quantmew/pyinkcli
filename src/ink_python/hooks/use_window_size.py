"""
useWindowSize hook for ink-python.

Provides terminal window size information.
"""

from __future__ import annotations

import shutil
from typing import Optional, Tuple

from ink_python.hooks._runtime import useState, useEffect


def useWindowSize() -> Tuple[int, int]:
    """
    Hook to get the terminal window size.

    Returns:
        Tuple of (width, height) in columns and rows.
    """
    def get_size() -> Tuple[int, int]:
        try:
            size = shutil.get_terminal_size()
            return (size.columns, size.lines)
        except Exception:
            return (80, 24)

    width, height = get_size()
    state = useState((width, height))

    def handle_resize():
        new_size = get_size()
        state[1](new_size)

    # Note: In a real implementation, we'd need to set up a signal handler
    # for SIGWINCH. For simplicity, we just return the current size.
    # The actual resize handling is done by the Ink class.

    return state[0]
