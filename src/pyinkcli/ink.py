from __future__ import annotations

import asyncio
from dataclasses import dataclass
import os
import signal
import threading
from types import SimpleNamespace
from typing import Any

from .component import createElement
from .components.App import create_app_tree, create_runtime_contexts
from .hooks import _runtime as hooks_runtime
from .hooks._runtime import _clear_hook_state, _set_rerender_callback, _set_schedule_update_callback
from .hooks.use_app import _set_current_app
from .hooks.use_input import _clear_input_handlers
from .hooks.use_paste import _clear_paste_handlers, _dispatch_paste
from .hooks.use_stderr import _StderrHandle, _set_stderr_handle
from .hooks.use_stdout import _StdoutHandle, _set_stdout_handle
from .hooks.use_window_size import _set_window_size
from .instances import delete_instance
from .packages.react_reconciler.ReactFiberWorkLoop import flushPendingEffects
from .reconciler import createReconciler, discreteUpdates
from .renderer import RenderResult, render_dom
from .render_to_string import create_root_node
from .runtime import AsyncLoopThread, ConsolePatch, ExitManager, OutputDriver, RenderScheduler, TerminalSession
from .suspense_runtime import _set_renderer_rerender
from .utils.ansi_escapes import enter_alternative_screen, exit_alternative_screen, hide_cursor_escape, show_cursor_escape
from .sanitize_ansi import sanitizeAnsi


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


class Ink:
    def __init__(self, options: Options) -> None:
        self.options = options
        self.stdout = options.stdout
        self.stdin = options.stdin
        self.stderr = options.stderr
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
        self._input_interest_count = 0
        self._paste_interest_count = 0
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
        self._root_node.onRender = lambda: None
        self._root_node.onImmediateRender = lambda: None
        self._reconciler = createReconciler(self._root_node)
        self._container = self._reconciler.create_container(self._root_node, tag=0)
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
        _set_renderer_rerender(self._rerender_current)

        stdout_handle = _StdoutHandle(self.stdout)
        stderr_handle = _StderrHandle(self.stderr)
        stdout_handle.bind_overlay_writer(self._write_to_stdout)
        stderr_handle.bind_overlay_writer(self._write_to_stderr)
        _set_stdout_handle(stdout_handle)
        _set_stderr_handle(stderr_handle)

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
            self._session.on_input(self._on_session_input)
            self._session.on_paste(self._on_session_paste)
            self._session.start()
            self._session.set_raw_mode(True)

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
        self._current_node = create_app_tree(
            raw_node,
            app=self,
            stdin=self.stdin,
            stdout=self.stdout,
            stderr=self.stderr,
            interactive=self.options.interactive,
        )
        self._reconciler._force_rerender = True
        try:
            self._perform_render(self._current_node)
        finally:
            self._reconciler._force_rerender = False

    def _rerender_explicit(self, node) -> None:
        self._reconciler._force_rerender = True
        try:
            self.render(node)
        finally:
            self._reconciler._force_rerender = False

    def _rerender_current(self) -> None:
        if self._current_node is not None and not self._is_unmounted:
            self._reconciler._force_rerender = True
            try:
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
            try:
                signal.signal(signal.SIGINT, self._previous_sigint_handler)
            except Exception:  # noqa: BLE001
                pass
        if self._previous_sigwinch_handler is not None and hasattr(signal, "SIGWINCH"):
            try:
                signal.signal(signal.SIGWINCH, self._previous_sigwinch_handler)
            except Exception:  # noqa: BLE001
                pass
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
        if self._scheduler is not None:
            self._scheduler.wait_for_idle(timeout or 0.1)
        remaining_timers = []
        for timer in self._transition_threads:
            if self._current_node is None:
                try:
                    timer.join(timeout or 0.1)
                except RuntimeError:
                    pass
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
        hooks_runtime._dirty_components.clear()
        self._container.render_state = None
        if self._exit_manager.has_error():
            return self.wait_until_exit(timeout)
        return None

    def clear(self) -> None:
        if hasattr(self.stdout, "truncate"):
            self.stdout.seek(0)
            self.stdout.truncate(0)

    def _request_commit_render(self, priority: str, immediate: bool = False) -> None:
        if immediate:
            self._root_node.onImmediateRender()
        else:
            self._root_node.onRender()

    def _prepare_stream_payload(self, stream, text: str) -> str:
        if hasattr(stream, "isatty") and stream.isatty() and not text.startswith("\x1b"):
            return text.replace("\n", "\r\n")
        return text

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
            try:
                size = os.get_terminal_size(self.stdout.fileno())
                if size.columns > 0 and size.lines > 0:
                    return size.columns, size.lines
            except OSError:
                pass
        return 80, 24

    def _reset_rendered_frame(self, *, preserve_height: bool = False) -> None:
        self._output_driver.log.clear()
        self._output_driver.last_output = ""
        self._output_driver.last_output_to_render = ""
        if not preserve_height:
            self._output_driver.last_output_height = 0

    def _on_render_callback(self) -> None:
        self._perform_render(self._current_node)

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

    def _perform_render(self, node) -> None:
        if node is None or self._is_unmounted:
            return
        with self._render_lock:
            try:
                if self._force_next_render:
                    self._reconciler._force_rerender = True
                self._reconciler.update_container_sync(node, self._container)
                if self.options.concurrent and self._transition_pending:
                    self._container.render_state = SimpleNamespace(status="pending", abort_reason=None)
                render_result = render_dom(self._root_node, self.options.screen_reader_enabled)
                self._rendered_output = render_result.output
                self._output_driver.render_frame(
                    self._rendered_output,
                    static_output=render_result.staticOutput,
                )
                flushPendingEffects()
                self._exit_manager.set_error(None)
            except Exception as error:  # noqa: BLE001
                self._exit_manager.set_error(error)
                self._rendered_output = f"ERROR\n{error}"
                self._output_driver.render_frame(self._rendered_output, force_clear=True)
            finally:
                if self._pending_session_exit_result is not None and self._session is not None:
                    pending_result = self._pending_session_exit_result
                    self._pending_session_exit_result = None
                    self._session.exit(pending_result)
                if self._force_next_render:
                    self._reconciler._force_rerender = False
                    self._force_next_render = False

    def _render_from_scheduler(self, _priority: str) -> None:
        self._perform_render(self._current_node)

    def _schedule_render(self, priority: str = "default") -> None:
        if self._scheduler is None:
            self._rerender_current()
            return
        self._scheduler.schedule_render(priority)

    def _run_discrete(self, callback) -> None:
        discreteUpdates(callback)

    def _set_cursor_position(self, position) -> None:
        self._log._cursor_position = position
        self._output_driver.set_cursor_position(position)
        if getattr(hooks_runtime, "_rendering", False):
            return
        self._schedule_render("discrete")

    def _on_session_input(self, value: str) -> None:
        from .hooks.use_input import _dispatch_input

        if value == "\x03":
            self.exit()
            return
        _dispatch_input(value)

    def _on_session_paste(self, value: str) -> None:
        _dispatch_paste(value)

    def _register_input_interest(self) -> None:
        self._input_interest_count += 1
        if self._session is not None:
            self._session.set_raw_mode(True)

    def _unregister_input_interest(self) -> None:
        if self._input_interest_count == 0:
            return
        self._input_interest_count -= 1
        if self._session is not None:
            self._session.set_raw_mode(False)

    def _register_paste_interest(self) -> None:
        self._paste_interest_count += 1
        if self._session is not None:
            self._session.set_raw_mode(True)
            self._session.set_bracketed_paste_mode(True)

    def _unregister_paste_interest(self) -> None:
        if self._paste_interest_count == 0:
            return
        self._paste_interest_count -= 1
        if self._session is not None:
            self._session.set_bracketed_paste_mode(False)
            self._session.set_raw_mode(False)



__all__ = ["Ink", "Options"]
