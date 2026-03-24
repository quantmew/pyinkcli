from __future__ import annotations

import sys

from .ink import Options


def get_options(stdout_or_options=None, **overrides):
    if isinstance(stdout_or_options, dict):
        options = dict(stdout_or_options)
    else:
        options = {}
        if stdout_or_options is not None:
            options["stdout"] = stdout_or_options
            options.setdefault("stdin", sys.stdin)
    options.update(overrides)
    return options


def _stream_is_tty(stream: object) -> bool:
    isatty = getattr(stream, "isatty", None)
    return bool(callable(isatty) and isatty())


def create_ink_options(resolved_options: dict) -> Options:
    stream = resolved_options.get("stdout", sys.stdout)
    input_stream = resolved_options.get("stdin", sys.stdin)
    error_stream = resolved_options.get("stderr", sys.stderr)
    interactive = resolved_options.get("interactive")
    if interactive is None:
        interactive = bool(_stream_is_tty(stream) and _stream_is_tty(input_stream))
    return Options(
        stdout=stream,
        stdin=input_stream,
        stderr=error_stream,
        debug=resolved_options.get("debug", False),
        interactive=interactive,
        patch_console=resolved_options.get("patch_console", resolved_options.get("patchConsole", True)),
        concurrent=resolved_options.get("concurrent", False),
        alternate_screen=resolved_options.get("alternate_screen", resolved_options.get("alternateScreen", False)),
        screen_reader_enabled=resolved_options.get("is_screen_reader_enabled", resolved_options.get("isScreenReaderEnabled", False)),
        max_fps=resolved_options.get("max_fps", resolved_options.get("maxFps", 30)),
        incremental_rendering=resolved_options.get("incremental_rendering", resolved_options.get("incrementalRendering", False)),
    )

__all__ = ["create_ink_options", "get_options"]
