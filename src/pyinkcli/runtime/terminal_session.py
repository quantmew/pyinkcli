from __future__ import annotations

import asyncio
import codecs
import concurrent.futures
import contextlib
import os
from collections.abc import Callable
from typing import Any

from ..input_parser import createInputParser
from .loop_thread import AsyncLoopThread

termios: Any | None
tty: Any | None

try:  # pragma: no cover
    import termios
    import tty
except ImportError:  # pragma: no cover
    termios = None
    tty = None


class TerminalSession:
    def __init__(self, stdin, stdout, loop_thread) -> None:
        self.stdin = stdin
        self.stdout = stdout
        self._loop_thread: AsyncLoopThread | None = loop_thread
        self._input_parser = createInputParser()
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self._input_callbacks: list[Callable[[str], None]] = []
        self._paste_callbacks: list[Callable[[str], None]] = []
        self._exit_event: asyncio.Event | None = None
        self._reader_installed = False
        self._escape_flush_handle: Any | None = None
        self._raw_mode_depth = 0
        self._bracketed_paste_depth = 0
        self._term_attrs: Any | None = None
        self._exit_result = None

    def start(self) -> None:
        if self._loop_thread is None:
            return
        self._loop_thread.submit(self._start_on_loop).result(timeout=1.0)

    def on_input(self, callback: Callable[[str], None]) -> None:
        self._input_callbacks.append(callback)

    def on_paste(self, callback: Callable[[str], None]) -> None:
        self._paste_callbacks.append(callback)

    def set_raw_mode(self, enabled: bool) -> None:
        if self._loop_thread is not None:
            future = self._loop_thread.submit(self._set_raw_mode_on_loop, enabled)
            try:
                future.result(timeout=1.0)
            except concurrent.futures.TimeoutError:
                # Avoid deadlocking effect cleanup while the loop is busy handling input/render work.
                self._loop_thread.call_soon(self._set_raw_mode_on_loop, enabled)

    def set_bracketed_paste_mode(self, enabled: bool) -> None:
        if self._loop_thread is not None:
            self._loop_thread.call_soon(self._set_bracketed_paste_mode_on_loop, enabled)

    def exit(self, result=None) -> None:
        self._exit_result = result
        if self._loop_thread is not None:
            self._loop_thread.call_soon(self._exit_on_loop, result)

    async def wait_until_exit(self):
        if self._exit_event is None:
            return self._exit_result
        await self._exit_event.wait()
        return self._exit_result

    def stop(self) -> None:
        if self._loop_thread is not None:
            self._loop_thread.submit(self._stop_on_loop).result(timeout=1.0)

    def _start_on_loop(self) -> None:
        loop_thread = self._loop_thread
        if loop_thread is None:
            return
        if self._exit_event is None:
            self._exit_event = asyncio.Event()
        if not hasattr(self.stdin, "fileno"):
            return
        if not hasattr(self.stdin, "isatty") or not self.stdin.isatty():
            return
        try:
            fileno = self.stdin.fileno()
        except Exception:  # noqa: BLE001
            return
        loop = loop_thread.loop
        if hasattr(loop, "add_reader"):
            loop.add_reader(fileno, self._handle_readable)
            self._reader_installed = True

    def _stop_on_loop(self) -> None:
        loop_thread = self._loop_thread
        if loop_thread is None:
            return
        if self._escape_flush_handle is not None:
            self._escape_flush_handle.cancel()
            self._escape_flush_handle = None
        if self._reader_installed and hasattr(self.stdin, "fileno"):
            with contextlib.suppress(Exception):  # noqa: BLE001
                loop_thread.loop.remove_reader(self.stdin.fileno())
            self._reader_installed = False
        self._restore_raw_mode()
        self._set_bracketed_paste_mode_on_loop(False, force=True)
        self._exit_on_loop(self._exit_result)

    def _exit_on_loop(self, result=None) -> None:
        self._exit_result = result
        if self._exit_event is not None and not self._exit_event.is_set():
            self._exit_event.set()

    def _handle_readable(self) -> None:
        try:
            chunk = os.read(self.stdin.fileno(), 4096)
        except OSError:
            self._exit_on_loop(None)
            return
        if not chunk:
            self._exit_on_loop(None)
            return
        text = self._decoder.decode(chunk)
        for event in self._input_parser.push(text):
            if getattr(event, "kind", "input") == "paste":
                self._emit_paste(event.data)
            else:
                self._emit_input(event.data)
        if self._input_parser.hasPendingEscape():
            self._schedule_pending_escape_flush()

    def _schedule_pending_escape_flush(self) -> None:
        loop_thread = self._loop_thread
        if loop_thread is None:
            return
        if self._escape_flush_handle is not None:
            self._escape_flush_handle.cancel()
        self._escape_flush_handle = loop_thread.loop.call_later(0.025, self._flush_pending_escape)

    def _flush_pending_escape(self) -> None:
        self._escape_flush_handle = None
        pending = self._input_parser.flushPendingEscape()
        if pending:
            self._emit_input(pending)

    def _emit_input(self, value: str) -> None:
        for callback in list(self._input_callbacks):
            callback(value)

    def _emit_paste(self, text: str) -> None:
        if self._paste_callbacks:
            for callback in list(self._paste_callbacks):
                callback(text)
            return
        self._emit_input(text)

    def _set_raw_mode_on_loop(self, enabled: bool) -> None:
        if enabled:
            self._raw_mode_depth += 1
            if self._raw_mode_depth == 1:
                self._enable_raw_mode()
            return
        if self._raw_mode_depth == 0:
            return
        self._raw_mode_depth -= 1
        if self._raw_mode_depth == 0:
            self._restore_raw_mode()

    def _set_bracketed_paste_mode_on_loop(self, enabled: bool, force: bool = False) -> None:
        if enabled:
            self._bracketed_paste_depth += 1
            if self._bracketed_paste_depth == 1:
                self.stdout.write("\x1b[?2004h")
            return
        if self._bracketed_paste_depth == 0 and not force:
            return
        self._bracketed_paste_depth = 0
        self.stdout.write("\x1b[?2004l")

    def _enable_raw_mode(self) -> None:
        if not hasattr(self.stdin, "isatty") or not self.stdin.isatty():
            return
        if hasattr(self.stdin, "setRawMode"):
            self.stdin.setRawMode(True)
            return
        if termios is None or tty is None or not hasattr(self.stdin, "fileno"):
            return
        try:
            fileno = self.stdin.fileno()
        except Exception:  # noqa: BLE001
            return
        self._term_attrs = termios.tcgetattr(fileno)
        tty.setraw(fileno)

    def _restore_raw_mode(self) -> None:
        if hasattr(self.stdin, "setRawMode"):
            self.stdin.setRawMode(False)
            return
        if termios is None or self._term_attrs is None or not hasattr(self.stdin, "fileno"):
            return
        try:
            fileno = self.stdin.fileno()
        except Exception:  # noqa: BLE001
            return
        termios.tcsetattr(fileno, termios.TCSADRAIN, self._term_attrs)
        self._term_attrs = None
