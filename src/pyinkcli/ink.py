from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import threading
import time
import traceback
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from .component import createElement
from .components.App import create_app_tree, create_runtime_contexts
from .hooks import _runtime as hooks_runtime
from .hooks._runtime import (
    _clear_hook_state,
    _set_rerender_callback,
    _set_schedule_update_callback,
    _set_trace_callback,
)
from .hooks.use_app import _set_current_app
from .hooks.use_input import _clear_input_handlers
from .hooks.use_paste import _clear_paste_handlers, _dispatch_paste
from .hooks.use_stdin import _set_stdin
from .hooks.use_stderr import _set_stderr_handle
from .hooks.use_stdout import _set_stdout_handle
from .hooks.use_window_size import _set_window_size
from .instances import delete_instance
from .packages.react_reconciler.ReactFiberWorkLoop import flushPendingEffects
from .packages.react_reconciler.ReactFiberLane import (
    DefaultLane,
    InputContinuousLane,
    IdleLane,
    SyncLane,
    TransitionLanes,
)
from .reconciler import createReconciler, discreteUpdates, _set_trace_callback as _set_reconciler_trace_callback
from .render_to_string import create_root_node
from .renderer import RenderResult as _RenderResult
from .renderer import render_dom
from .runtime import (
    AsyncLoopThread,
    ConsolePatch,
    ExitManager,
    OutputDriver,
    RenderScheduler,
    TerminalSession,
)
from .sanitize_ansi import sanitizeAnsi
from .suspense_runtime import _set_renderer_rerender
from .utils.ansi_escapes import (
    enter_alternative_screen,
    exit_alternative_screen,
    hide_cursor_escape,
    show_cursor_escape,
)

RenderResult = _RenderResult


@dataclass
class Options:
    stdout: object
    stdin: object
    stderr: object
    debug: bool = False
    interactive: bool = False
    patch_console: bool = False
    concurrent: bool = False
    alternate_screen: bool = False
    screen_reader_enabled: bool = False
    max_fps: int = 30
    incremental_rendering: bool = False
    trace_updates: bool = False


class Ink:
    def __init__(self, options: Options) -> None:
        self.options = options
        self.stdout = options.stdout
        self.stdin = options.stdin
        self.stderr = options.stderr
        env_trace = os.environ.get("PYINK_TRACE_UPDATES", "").lower() in {"1", "true", "yes", "on"}
        self._trace_enabled = bool(options.trace_updates or env_trace)
        self._trace_events: list[dict[str, Any]] = []
        self._trace_seq = 0
        self._is_unmounted = False
        self._current_node = None
        self._rendered_output = ""
        self._transition_pending = False
        self._transition_threads: list[threading.Timer] = []
        self._render_lock = threading.RLock()
        self._loop_thread: AsyncLoopThread | None = None
        self._scheduler: RenderScheduler | None = None
        self._session: TerminalSession | None = None
        self._exit_manager = ExitManager()
        self._pending_session_exit_result: Any | None = None
        self._console_patch = ConsolePatch(self._write_to_stdout, self._write_to_stderr, self.stdout, self.stderr)
        self._previous_sigint_handler = None
        self._previous_sigwinch_handler = None
        self._force_next_render = False
        hooks_runtime._dirty_components.clear()
        hooks_runtime._render_phase_rerender_count = 0
        initial_width, initial_height = self._get_stream_dimensions()
        self._last_terminal_width = initial_width
        self._root_node = create_root_node(
            initial_width,
            None,
        )
        self._root_node.onComputeLayout = lambda: None
        self._root_node.onRender = lambda: self._request_commit_render("default")
        self._root_node.onImmediateRender = lambda: self._request_commit_render(
            "discrete",
            immediate=True,
        )
        self._reconciler = createReconciler(self._root_node)
        self._container = self._reconciler.create_container(
            self._root_node,
            tag=1 if options.concurrent else 0,
        )
        self._reconciler.set_commit_handlers(
            on_commit=lambda: self._request_commit_render("default"),
            on_immediate_commit=lambda: self._request_commit_render(
                "discrete",
                immediate=True,
            ),
        )
        self._runtime_contexts = create_runtime_contexts(
            app=self,
            stdin=self.stdin,
            stdout=self.stdout,
            stderr=self.stderr,
            interactive=options.interactive,
        )
        self.rerender = self._rerender_explicit
        self.cleanup = self.unmount
        _set_current_app(self)
        _set_rerender_callback(self._rerender_current)
        _set_schedule_update_callback(lambda fiber, priority: self._schedule_render(priority))
        _set_trace_callback(self._trace)
        _set_reconciler_trace_callback(self._trace)
        _set_renderer_rerender(self._rerender_current)

        _set_stdin(handle=self._runtime_contexts["stdin"])
        _set_stdout_handle(self._runtime_contexts["stdout"])
        _set_stderr_handle(self._runtime_contexts["stderr"])

        _set_window_size(
            initial_width,
            initial_height,
        )

        self._output_driver = OutputDriver(
            self.stdout,
            interactive=options.interactive,
            debug=options.debug,
            incremental=options.incremental_rendering,
        )
        self._log = self._output_driver.log

        if options.interactive and hasattr(self.stdin, "isatty") and self.stdin.isatty():
            self._loop_thread = AsyncLoopThread()
            self._scheduler = RenderScheduler(
                self._loop_thread,
                self._render_from_scheduler,
                max_fps=options.max_fps,
            )
            self._session = TerminalSession(self.stdin, self.stdout, self._loop_thread)
            self._runtime_contexts["stdin"].bind_runtime(
                session=self._session,
                loop_thread=self._loop_thread,
                on_exit=self.exit,
            )
            self._session.on_input(self._on_session_input)
            self._session.start()

        if options.alternate_screen and options.interactive:
            self._write_stream(self.stdout, enter_alternative_screen() + hide_cursor_escape)
        if options.patch_console and not options.debug:
            self._console_patch.patch()
        if options.interactive:
            try:
                self._previous_sigint_handler = signal.getsignal(signal.SIGINT)
                signal.signal(signal.SIGINT, lambda _signum, _frame: self.exit())
            except Exception:  # noqa: BLE001
                self._previous_sigint_handler = None
            if hasattr(signal, "SIGWINCH"):
                try:
                    self._previous_sigwinch_handler = signal.getsignal(signal.SIGWINCH)
                    signal.signal(signal.SIGWINCH, lambda _signum, _frame: self._handle_resize())
                except Exception:  # noqa: BLE001
                    self._previous_sigwinch_handler = None

    def render(self, node) -> None:
        raw_node = createElement(node) if callable(node) and not getattr(node, "type", None) else node
        self._trace("ink.render_root", explicit=True)
        self._current_node = create_app_tree(
            raw_node,
            contexts=self._runtime_contexts,
        )
        self._reconciler._force_rerender = True
        try:
            if self.options.concurrent and self._scheduler is not None:
                self._schedule_render("default")
            else:
                self._perform_render(self._current_node)
        finally:
            self._reconciler._force_rerender = False

    def _rerender_explicit(self, node) -> None:
        self._trace("ink.render_explicit")
        self._reconciler._force_rerender = True
        try:
            self.render(node)
        finally:
            self._reconciler._force_rerender = False

    def _rerender_current(self) -> None:
        self._trace("ink.rerender_current", has_node=self._current_node is not None)
        if self._current_node is not None and not self._is_unmounted:
            self._reconciler._force_rerender = True
            try:
                if self.options.concurrent and self._scheduler is not None:
                    self._schedule_render("default")
                else:
                    self._perform_render(self._current_node)
            finally:
                self._reconciler._force_rerender = False

    def unmount(self) -> None:
        if self._is_unmounted:
            return
        self._is_unmounted = True
        delete_instance(self.stdout)
        for child in list(getattr(self._root_node, "childNodes", [])):
            self._reconciler._invoke_component_will_unmount(child)
        _clear_input_handlers()
        _clear_paste_handlers()
        _clear_hook_state()
        _set_rerender_callback(None)
        _set_schedule_update_callback(None)
        _set_trace_callback(None)
        _set_reconciler_trace_callback(None)
        _set_current_app(None)
        _set_renderer_rerender(None)
        if self._session is not None:
            self._session.stop()
        self._output_driver.finish()
        self._console_patch.restore()
        if self.options.alternate_screen and self.options.interactive:
            self._write_stream(
                self.stdout,
                show_cursor_escape + show_cursor_escape + show_cursor_escape + exit_alternative_screen(),
            )
        if self._previous_sigint_handler is not None:
            with contextlib.suppress(Exception):  # noqa: BLE001
                signal.signal(signal.SIGINT, self._previous_sigint_handler)
        if self._previous_sigwinch_handler is not None and hasattr(signal, "SIGWINCH"):
            with contextlib.suppress(Exception):  # noqa: BLE001
                signal.signal(signal.SIGWINCH, self._previous_sigwinch_handler)
        if self._loop_thread is not None:
            self._loop_thread.stop()

    def wait_until_exit(self, timeout: float | None = None):
        if self._session is None:
            return self._exit_manager.wait_until_exit(self.unmount, self.wait_until_render_flush, timeout=timeout)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.wait_until_exit_async(timeout=timeout))
        raise RuntimeError("wait_until_exit() cannot be called inside a running event loop; use wait_until_exit_async()")

    async def wait_until_exit_async(self, timeout: float | None = None):
        if self._session is None:
            return self._exit_manager.result
        result = await self._exit_manager.wait_until_exit_async(
            self.unmount,
            self._session,
            self._loop_thread,
            timeout=timeout,
        )
        if not self._is_unmounted:
            self.unmount()
        return result

    def exit(self, error_or_result: Any = None) -> None:
        self._exit_manager.set_result(error_or_result)
        if self._session is not None:
            if getattr(hooks_runtime, "_batched_mode", None) is not None and self._loop_thread is not None:
                if getattr(hooks_runtime, "_batched_pending", False):
                    self._pending_session_exit_result = error_or_result
                    return
                self._loop_thread.call_soon(self._session.exit, error_or_result)
                return
            self._session.exit(error_or_result)
            return
        self.unmount()

    def waitUntilExit(self, timeout: float | None = None):
        return self.wait_until_exit(timeout=timeout)

    def waitUntilRenderFlush(self, timeout: float | None = None):
        return self.wait_until_render_flush(timeout=timeout)

    def wait_until_render_flush(self, timeout: float | None = None):
        self._trace("ink.wait_until_render_flush", timeout=timeout)
        if self._scheduler is not None:
            self._scheduler.wait_for_idle(timeout or 0.1)
        remaining_timers = []
        for timer in self._transition_threads:
            if self._current_node is None:
                with contextlib.suppress(RuntimeError):
                    timer.join(timeout or 0.1)
            if timer.is_alive():
                remaining_timers.append(timer)
        self._transition_threads = remaining_timers
        flushPendingEffects()
        if getattr(hooks_runtime, "_dirty_components", None):
            self._reconciler._force_rerender = True
            try:
                self._perform_render(self._current_node)
            finally:
                self._reconciler._force_rerender = False
            hooks_runtime._dirty_components.clear()
        self._trace("ink.wait_until_render_flush_end", dirty_components=bool(hooks_runtime._dirty_components))
        hooks_runtime._dirty_components.clear()
        self._container.render_state = None
        if self._exit_manager.has_error():
            return self.wait_until_exit(timeout)
        return None

    def clear(self) -> None:
        if hasattr(self.stdout, "truncate"):
            self.stdout.seek(0)
            self.stdout.truncate(0)

    def clear_trace(self) -> None:
        self._trace_events.clear()

    def get_trace(self) -> list[dict[str, Any]]:
        return list(self._trace_events)

    def get_trace_events(
        self,
        *,
        source: str | None = None,
        event_prefix: str | None = None,
        since_seq: int = 0,
        start_ts: int | None = None,
        end_ts: int | None = None,
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for event in self._trace_events:
            if event.get("seq", -1) < since_seq:
                continue
            if start_ts is not None and event.get("ts", 0) < start_ts:
                continue
            if end_ts is not None and event.get("ts", 0) > end_ts:
                continue
            if source is not None and event.get("source") != source:
                continue
            if event_prefix is not None and not str(event.get("event", "")).startswith(event_prefix):
                continue
            events.append(event)
        return events

    def get_trace_timeline(
        self,
        *,
        source: str | None = None,
        event_prefix: str | None = None,
        since_seq: int = 0,
        max_items: int | None = None,
    ) -> list[dict[str, Any]]:
        events = self.get_trace_events(
            source=source,
            event_prefix=event_prefix,
            since_seq=since_seq,
        )
        if max_items is not None and max_items > 0:
            events = events[:max_items]
        timeline: list[dict[str, Any]] = []
        prev_ts = None
        for event in events:
            delta_ns = None
            if prev_ts is not None:
                delta_ns = event.get("ts", 0) - prev_ts
            prev_ts = event.get("ts", 0)
            timeline.append(
                {
                    "seq": event.get("seq"),
                    "source": event.get("source"),
                    "event": event.get("event"),
                    "delta_ns": delta_ns,
                    "fields": {
                        k: v
                        for k, v in event.items()
                        if k not in {"seq", "source", "event", "ts"}
                    },
                }
            )
        return timeline

    def _trace(self, event: str, **fields: Any) -> None:
        if not self._trace_enabled:
            return
        record = {
            "source": "ink",
            "seq": self._trace_seq,
            "event": event,
            "ts": time.perf_counter_ns(),
        }
        self._trace_seq += 1
        record.update(fields)
        self._trace_events.append(record)

    def _request_commit_render(self, priority: str = "default", immediate: bool = False) -> None:
        self._trace(
            "ink.commit_request",
            priority=priority,
            immediate=immediate,
        )
        self._render_frame(immediate=immediate)

    def _prepare_stream_payload(self, stream, text: str) -> str:
        if hasattr(stream, "isatty") and stream.isatty() and not text.startswith("\x1b"):
            return text.replace("\n", "\r\n")
        return text

    def _normalize_render_priority(self, priority):
        if isinstance(priority, str):
            if priority == "continuous":
                return "discrete"
            if priority in {"discrete", "default", "transition", "render_phase"}:
                return "default" if priority == "render_phase" else priority
            return "default"
        if isinstance(priority, int):
            if SyncLane & priority or InputContinuousLane & priority:
                return "discrete"
            if DefaultLane & priority:
                return "default"
            if TransitionLanes & priority:
                return "transition"
            if IdleLane & priority:
                return "default"
        return "default"

    def _write_stream(self, stream, text: str) -> None:
        stream.write(self._prepare_stream_payload(stream, text))

    def _write_to_stdout(self, text: str) -> None:
        payload = self._prepare_stream_payload(self.stdout, sanitizeAnsi(text))
        if not self.options.interactive:
            self.stdout.write(payload)
            return
        self._output_driver.overlay_stdout(payload)

    def _write_to_stderr(self, text: str) -> None:
        payload = self._prepare_stream_payload(self.stderr, sanitizeAnsi(text))
        if "The above error occurred in the <" in payload:
            return
        self.stderr.write(payload)

    def _handle_resize(self) -> None:
        width, height = self._get_stream_dimensions()
        self._trace("ink.resize", width=width, height=height)
        if width < self._last_terminal_width:
            self._reset_rendered_frame(preserve_height=True)
        self._root_node.width = width
        self._root_node.height = None
        _set_window_size(width, height)
        self._last_terminal_width = width
        self._force_next_render = True
        self._schedule_render("discrete")

    def _get_stream_dimensions(self) -> tuple[int, int]:
        columns = getattr(self.stdout, "columns", None)
        rows = getattr(self.stdout, "rows", None)
        if isinstance(columns, int) and columns > 0 and isinstance(rows, int) and rows > 0:
            return columns, rows
        if hasattr(self.stdout, "isatty") and self.stdout.isatty() and hasattr(self.stdout, "fileno"):
            with contextlib.suppress(OSError):
                size = os.get_terminal_size(self.stdout.fileno())
                if size.columns > 0 and size.lines > 0:
                    return size.columns, size.lines
        return 80, 24

    def _reset_rendered_frame(self, *, preserve_height: bool = False) -> None:
        self._output_driver.log.clear()
        self._output_driver.last_output = ""
        self._output_driver.last_output_to_render = ""
        if not preserve_height:
            self._output_driver.last_output_height = 0

    def _read_stdin_chunk(self) -> str:
        data = self.stdin.buffer.read(1)
        if not data:
            return ""
        collected = data
        while True:
            try:
                return collected.decode("utf-8")
            except UnicodeDecodeError as error:
                if error.reason == "unexpected end of data":
                    next_byte = self.stdin.buffer.read(1)
                    if not next_byte:
                        return collected.decode("utf-8", "replace")
                    collected += next_byte
                    continue
                return collected.decode("utf-8", "replace")

    def _schedule_transition(self, callback, delay: float = 0.0) -> None:
        timer = threading.Timer(delay, callback)
        self._transition_threads.append(timer)
        timer.start()

    def _render_output(self) -> str:
        return render_dom(self._root_node, self.options.screen_reader_enabled).output

    def _render_frame(self, immediate: bool = False) -> None:
        if self._is_unmounted or self._current_node is None:
            return
        try:
            self._trace("ink.render_frame_begin", immediate=immediate)
            render_result = render_dom(self._root_node, self.options.screen_reader_enabled)
            self._rendered_output = render_result.output
            self._output_driver.render_frame(
                self._rendered_output,
                static_output=render_result.staticOutput,
            )
            self._trace(
                "ink.render_frame_end",
                output_len=len(self._rendered_output),
                static_len=len(render_result.staticOutput),
                immediate=immediate,
            )
            flushPendingEffects()
            self._exit_manager.set_error(None)
        except Exception as error:  # noqa: BLE001
            self._trace("ink.render_frame_error", error=repr(error))
            self._exit_manager.set_error(error)
            self._rendered_output = "ERROR\n" + "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            ).rstrip()
            self._output_driver.render_frame(self._rendered_output, force_clear=True)

    def _perform_render(self, node) -> None:
        if node is None or self._is_unmounted:
            return
        self._trace("ink.perform_render_begin", node_type=type(node).__name__)
        with self._render_lock:
            try:
                if self._force_next_render:
                    self._reconciler._force_rerender = True
                if self._container.tag == 1:
                    self._reconciler.update_container(node, self._container)
                    self._reconciler._flush_pending(self._container)
                else:
                    self._reconciler.update_container_sync(node, self._container)
                if self.options.concurrent and self._transition_pending:
                    self._container.render_state = SimpleNamespace(status="pending", abort_reason=None)
                self._trace("ink.perform_render_end", success=True)
            except Exception as error:  # noqa: BLE001
                self._trace("ink.perform_render_error", error=repr(error))
                self._exit_manager.set_error(error)
                self._rendered_output = "ERROR\n" + "".join(
                    traceback.format_exception(type(error), error, error.__traceback__)
                ).rstrip()
                self._output_driver.render_frame(self._rendered_output, force_clear=True)
            finally:
                if self._pending_session_exit_result is not None and self._session is not None:
                    pending_result = self._pending_session_exit_result
                    self._pending_session_exit_result = None
                    self._session.exit(pending_result)
                if self._force_next_render:
                    self._reconciler._force_rerender = False
                    self._force_next_render = False

    def _render_from_scheduler(self, priority) -> None:
        _ = self._normalize_render_priority(priority)
        self._trace("ink.render_from_scheduler", priority=priority)
        self._perform_render(self._current_node)

    def _schedule_render(self, priority: str = "default") -> None:
        normalized = self._normalize_render_priority(priority)
        self._trace(
            "ink.schedule_render",
            requested=priority,
            normalized=normalized,
            with_scheduler=bool(self._scheduler is not None),
        )
        if self._scheduler is None:
            self._rerender_current()
            return
        self._scheduler.schedule_render(normalized)

    def _run_discrete(self, callback) -> None:
        self._trace("ink.discrete_begin")
        discreteUpdates(callback)
        self._trace("ink.discrete_end")

    def _set_cursor_position(self, position) -> None:
        self._log._cursor_position = position
        self._output_driver.set_cursor_position(position)
        if getattr(hooks_runtime, "_rendering", False):
            return
        self._schedule_render("discrete")

    def _on_session_input(self, value: str) -> None:
        self._runtime_contexts["stdin"].process_input_chunk(value)



__all__ = ["Ink", "Options"]
