"""
Public render entry split from `ink.py`.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, Callable, Optional, TextIO, Union

from pyinkcli.ink import Ink

if TYPE_CHECKING:
    from pyinkcli.component import RenderableNode


def render(
    node: "RenderableNode | Callable",
    *,
    stdout: Optional[TextIO] = None,
    stdin: Optional[TextIO] = None,
    stderr: Optional[TextIO] = None,
    **kwargs: Any,
) -> Any:
    return Ink.mount(
        node,
        stdout=stdout or sys.stdout,
        stdin=stdin or sys.stdin,
        stderr=stderr or sys.stderr,
        **kwargs,
    )
