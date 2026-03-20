"""
Public render entry split from `ink.py`.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TextIO

from pyinkcli.ink import Ink

if TYPE_CHECKING:
    from pyinkcli.component import RenderableNode


def render(
    node: RenderableNode | Callable,
    *,
    stdout: TextIO | None = None,
    stdin: TextIO | None = None,
    stderr: TextIO | None = None,
    **kwargs: Any,
) -> Any:
    return Ink.mount(
        node,
        stdout=stdout or sys.stdout,
        stdin=stdin or sys.stdin,
        stderr=stderr or sys.stderr,
        **kwargs,
    )
