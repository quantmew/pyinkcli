from __future__ import annotations

import asyncio
import codecs
import contextlib
import os
from collections.abc import Callable
from typing import Any

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
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self._input_callbacks: list[Callable[[str], None]] = []
        self._exit_event: asyncio.Event | None = None
        self._reader_installed = False
        self._term_attrs: Any | None = None
        self._exit_result = None
        self._desired_raw_mode = False
        self._desired_bracketed_paste = False
        self._raw_mode_enabled = False
        self._bracketed_paste_enabled = False

    def start(self) -> None:
        if self._loop_thread is None:
            return
        self._loop_thread.submit(self._start_on_loop).result(timeout=1.0)

    def on_input(self, callback: Callable[[str], None]) -> None:
        self._input_callbacks.append(callback)

    def set_raw_mode(self, enabled: bool) -> None:
        self.request_terminal_modes(
            raw_mode=enabled or self._desired_bracketed_paste,
            bracketed_paste=self._desired_bracketed_paste,
        )

    def set_bracketed_paste_mode(self, enabled: bool) -> None:
        self.request_terminal_modes(
            raw_mode=self._desired_raw_mode or enabled,
            bracketed_paste=enabled,
        )

    def request_terminal_modes(self, *, raw_mode: bool, bracketed_paste: bool) -> None:
        self._desired_raw_mode = bool(raw_mode or bracketed_paste)
        self._desired_bracketed_paste = bool(bracketed_paste)
        if self._loop_thread is not None:
            self._loop_thread.call_soon(self._apply_requested_terminal_modes_on_loop)

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
        self._apply_requested_terminal_modes_on_loop()

    def _stop_on_loop(self) -> None:
        loop_thread = self._loop_thread
        if loop_thread is None:
            return
        if self._reader_installed and hasattr(self.stdin, "fileno"):
            with contextlib.suppress(Exception):  # noqa: BLE001
                loop_thread.loop.remove_reader(self.stdin.fileno())
            self._reader_installed = False
        self._desired_raw_mode = False
        self._desired_bracketed_paste = False
        self._apply_requested_terminal_modes_on_loop(force=True)
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
        self._emit_input(text)

    def _emit_input(self, value: str) -> None:
        for callback in list(self._input_callbacks):
            callback(value)

    def _set_raw_mode_on_loop(self, enabled: bool) -> None:
        self._desired_raw_mode = bool(enabled or self._desired_bracketed_paste)
        self._apply_requested_terminal_modes_on_loop()

    def _apply_requested_terminal_modes_on_loop(self, force: bool = False) -> None:
        want_paste = bool(self._desired_bracketed_paste)
        want_raw = bool(self._desired_raw_mode or want_paste)

        if force or want_paste != self._bracketed_paste_enabled:
            self._set_bracketed_paste_mode_on_loop(want_paste, force=force)
        if force or want_raw != self._raw_mode_enabled:
            self._set_raw_mode_state_on_loop(want_raw)

    def _set_raw_mode_state_on_loop(self, enabled: bool) -> None:
        if enabled:
            if not self._raw_mode_enabled:
                self._raw_mode_enabled = True
                self._enable_raw_mode()
            return
        if self._raw_mode_enabled:
            self._raw_mode_enabled = False
            self._restore_raw_mode()

    def _set_bracketed_paste_mode_on_loop(self, enabled: bool, force: bool = False) -> None:
        if enabled:
            if force or not self._bracketed_paste_enabled:
                self._bracketed_paste_enabled = True
                self.stdout.write("\x1b[?2004h")
            return
        if force or self._bracketed_paste_enabled:
            self._bracketed_paste_enabled = False
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
