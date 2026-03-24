from __future__ import annotations

from collections import defaultdict
import sys
from typing import Any

from ..input_parser import createInputParser
from ..parse_keypress import parseKeypress

termios: Any | None
tty: Any | None

try:  # pragma: no cover
    import termios
    import tty
except ImportError:  # pragma: no cover
    termios = None
    tty = None

class _StdinHandle:
    def __init__(
        self,
        stream=None,
        output_stream=None,
        *,
        is_raw_mode_supported: bool | None = None,
        exit_on_ctrl_c: bool = True,
        internal_event_emitter=None,
        on_exit=None,
    ) -> None:
        self.stdin = stream or sys.stdin
        self._output_stream = output_stream or self.stdin
        self._listeners = defaultdict(list) if internal_event_emitter is None else internal_event_emitter._listeners
        self._is_raw_mode_supported = is_raw_mode_supported
        self.internal_exitOnCtrlC = exit_on_ctrl_c
        self.internal_eventEmitter = self
        self._on_exit = on_exit
        self._session = None
        self._loop_thread = None
        self._input_parser = createInputParser()
        self._escape_flush_handle = None
        self._pending_escape_flush_delay = 0.02
        self._raw_mode_enabled_count = 0
        self._bracketed_paste_enabled_count = 0
        self._raw_mode_active = False
        self._bracketed_paste_active = False
        self._term_attrs = None

    def on(self, event: str, listener) -> None:
        if listener not in self._listeners[event]:
            self._listeners[event].append(listener)

    def off(self, event: str, listener) -> None:
        listeners = self._listeners[event]
        if listener in listeners:
            listeners.remove(listener)

    def emit(self, event: str, *args) -> None:
        for listener in list(self._listeners[event]):
            listener(*args)

    def listener_count(self, event: str) -> int:
        return len(self._listeners[event])

    def clear(self, event: str | None = None) -> None:
        if event is None:
            self._listeners.clear()
        else:
            self._listeners[event].clear()

    @property
    def is_raw_mode_supported(self) -> bool:
        if self._is_raw_mode_supported is not None:
            return self._is_raw_mode_supported
        isatty = getattr(self.stdin, "isatty", None)
        return bool(callable(isatty) and isatty())

    @property
    def isRawModeSupported(self) -> bool:
        return self.is_raw_mode_supported

    def bind_runtime(self, *, session=None, loop_thread=None, on_exit=None) -> None:
        if session is not None:
            self._session = session
        if loop_thread is not None:
            self._loop_thread = loop_thread
        if on_exit is not None:
            self._on_exit = on_exit

    def _sync_terminal_modes(self) -> None:
        wants_paste = self._bracketed_paste_enabled_count > 0
        wants_raw = self._raw_mode_enabled_count > 0 or wants_paste
        self._set_bracketed_paste_mode_state(wants_paste)
        self._set_raw_mode_state(wants_raw)

    def _set_raw_mode_state(self, enabled: bool) -> None:
        if enabled:
            if not self._raw_mode_active:
                self._enable_raw_mode()
                self._raw_mode_active = True
            return
        if self._raw_mode_active:
            self._restore_raw_mode()
            self._raw_mode_active = False

    def _set_bracketed_paste_mode_state(self, enabled: bool) -> None:
        if enabled:
            if not self._bracketed_paste_active:
                self._bracketed_paste_active = True
                self._write_terminal_mode("\x1b[?2004h")
            return
        if self._bracketed_paste_active:
            self._bracketed_paste_active = False
            self._write_terminal_mode("\x1b[?2004l")

    def _write_terminal_mode(self, data: str) -> None:
        if not hasattr(self._output_stream, "write"):
            return
        try:
            self._output_stream.write(data)
            flush = getattr(self._output_stream, "flush", None)
            if callable(flush):
                flush()
        except Exception:
            pass

    def _enable_raw_mode(self) -> None:
        if not self.is_raw_mode_supported:
            return
        if hasattr(self.stdin, "setRawMode"):
            try:
                self.stdin.setRawMode(True)
            except Exception:
                pass
            return
        if termios is None or tty is None or not hasattr(self.stdin, "fileno"):
            return
        try:
            fileno = self.stdin.fileno()
        except Exception:
            return
        try:
            self._term_attrs = termios.tcgetattr(fileno)
            tty.setraw(fileno)
        except Exception:
            self._term_attrs = None

    def _restore_raw_mode(self) -> None:
        if hasattr(self.stdin, "setRawMode"):
            try:
                self.stdin.setRawMode(False)
            except Exception:
                pass
            return
        if termios is None or self._term_attrs is None or not hasattr(self.stdin, "fileno"):
            return
        try:
            fileno = self.stdin.fileno()
            termios.tcsetattr(fileno, termios.TCSADRAIN, self._term_attrs)
        except Exception:
            pass
        self._term_attrs = None

    def set_raw_mode(self, value: bool) -> None:
        if value:
            self._raw_mode_enabled_count += 1
        elif self._raw_mode_enabled_count > 0:
            self._raw_mode_enabled_count -= 1
            if self._raw_mode_enabled_count == 0:
                self._clear_pending_escape_flush()
                self._input_parser.reset()
        self._sync_terminal_modes()

    def set_bracketed_paste_mode(self, value: bool) -> None:
        if value:
            self._bracketed_paste_enabled_count += 1
        elif self._bracketed_paste_enabled_count > 0:
            self._bracketed_paste_enabled_count -= 1
        self._sync_terminal_modes()

    def setRawMode(self, value: bool) -> None:
        self.set_raw_mode(value)

    def setBracketedPasteMode(self, value: bool) -> None:
        self.set_bracketed_paste_mode(value)

    def _clear_pending_escape_flush(self) -> None:
        if self._escape_flush_handle is None:
            return
        self._escape_flush_handle.cancel()
        self._escape_flush_handle = None

    def _schedule_pending_escape_flush(self) -> None:
        self._clear_pending_escape_flush()
        if self._loop_thread is None:
            return
        self._escape_flush_handle = self._loop_thread.loop.call_later(
            self._pending_escape_flush_delay,
            self._flush_pending_escape,
        )

    def _flush_pending_escape(self) -> None:
        self._escape_flush_handle = None
        pending = self._input_parser.flushPendingEscape()
        if pending:
            self._emit_input(pending)

    def _collapse_navigation_events(self, events: list[Any]) -> list[Any]:
        collapsed: list[Any] = []
        pending_navigation: Any | None = None

        def flush_pending() -> None:
            nonlocal pending_navigation
            if pending_navigation is not None:
                collapsed.append(pending_navigation)
                pending_navigation = None

        for event in events:
            if getattr(event, "kind", "input") != "input":
                flush_pending()
                collapsed.append(event)
                continue

            parsed = parseKeypress(getattr(event, "data", ""))
            is_plain_arrow = (
                parsed.name in {"up", "down", "left", "right"}
                and not parsed.ctrl
                and not parsed.meta
                and not parsed.shift
                and not parsed.option
                and not parsed.super
                and not parsed.hyper
            )

            if parsed.eventType == "release" and is_plain_arrow:
                continue

            if is_plain_arrow:
                pending_navigation = event
                continue

            flush_pending()
            collapsed.append(event)

        flush_pending()
        return collapsed

    def _emit_input(self, value: str) -> None:
        if value == "\x03" and self.internal_exitOnCtrlC:
            if callable(self._on_exit):
                self._on_exit()
            return
        self.emit("input", value)

    def _emit_paste(self, text: str) -> None:
        if self.listener_count("paste") == 0:
            self._emit_input(text)
            return
        self.emit("paste", text)

    def process_input_chunk(self, text: str) -> None:
        self._clear_pending_escape_flush()
        events = self._collapse_navigation_events(self._input_parser.push(text))
        for event in events:
            if getattr(event, "kind", "input") == "paste":
                self._emit_paste(event.data)
            else:
                self._emit_input(event.data)
        if self._input_parser.hasPendingEscape():
            self._schedule_pending_escape_flush()


_stdin = _StdinHandle()


def useStdin() -> _StdinHandle:
    from ..components.StdinContext import StdinContext

    return StdinContext.current_value


def useStdinContext() -> _StdinHandle:
    from ..components.StdinContext import StdinContext

    return StdinContext.current_value


def _set_stdin(stream=None, output_stream=None, handle: _StdinHandle | None = None) -> None:
    global _stdin
    from ..components.StdinContext import StdinContext

    _stdin = handle or _StdinHandle(stream, output_stream)
    StdinContext.current_value = _stdin


__all__ = ["useStdin", "useStdinContext", "_StdinHandle", "_set_stdin"]
