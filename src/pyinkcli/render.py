from __future__ import annotations

import sys

from .component import createElement
from .hooks.use_app import _set_current_app
from .ink import Ink
from .render_helpers import create_ink_options, get_options
from .render_instance import get_instance


def render(node, stdout=None, stdin=None, stderr=None, **options):
    resolved_options = get_options(
        stdout,
        stdin=stdin or sys.stdin,
        stderr=stderr or sys.stderr,
        **options,
    )
    ink_options = create_ink_options(resolved_options)
    stream = ink_options.stdout
    error_stream = ink_options.stderr
    ink = get_instance(
        stream,
        lambda: Ink(ink_options),
        warning_stream=error_stream,
    )
    ink.render(createElement(node) if callable(node) else node)
    _set_current_app(ink)
    return ink


__all__ = ["get_options", "render"]
