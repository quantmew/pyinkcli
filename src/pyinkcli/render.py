from __future__ import annotations

from io import StringIO

from .hooks.use_app import _set_current_app
from .ink import Ink, Options
from .component import createElement


def render(node, stdout=None, stdin=None, stderr=None, **options):
    stream = stdout or StringIO()
    input_stream = stdin or StringIO()
    error_stream = stderr or stream
    ink = Ink(
        Options(
            stdout=stream,
            stdin=input_stream,
            stderr=error_stream,
            debug=options.get("debug", False),
            interactive=options.get("interactive", False),
            patch_console=options.get("patch_console", options.get("patchConsole", True)),
            concurrent=options.get("concurrent", False),
            alternate_screen=options.get("alternate_screen", options.get("alternateScreen", False)),
        )
    )
    ink.render(createElement(node) if callable(node) else node)
    _set_current_app(ink)
    return ink


__all__ = ["render"]
