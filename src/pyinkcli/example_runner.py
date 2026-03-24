from __future__ import annotations

import sys

from .render import render


class _ExampleStreamProxy:
    def __init__(self, stream, *, columns: int = 120, rows: int = 60) -> None:
        self._stream = stream
        self.columns = columns
        self.rows = rows

    def write(self, text: str):
        return self._stream.write(text)

    def flush(self):
        flush = getattr(self._stream, "flush", None)
        if callable(flush):
            return flush()
        return None

    def isatty(self) -> bool:
        return False

    def __getattr__(self, name: str):
        return getattr(self._stream, name)


def is_interactive_terminal() -> bool:
    return bool(
        callable(getattr(sys.stdout, "isatty", None))
        and sys.stdout.isatty()
        and callable(getattr(sys.stdin, "isatty", None))
        and sys.stdin.isatty()
    )


def run_example(node, **render_kwargs):
    interactive = render_kwargs.pop("interactive", None)
    if interactive is None:
        interactive = is_interactive_terminal()
    if not interactive and "stdout" not in render_kwargs:
        render_kwargs["stdout"] = _ExampleStreamProxy(sys.stdout)
    app = render(node, interactive=interactive, **render_kwargs)
    if interactive:
        return app.wait_until_exit()
    app.unmount()
    return app


__all__ = ["is_interactive_terminal", "run_example"]
