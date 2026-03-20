"""
Main Ink class for pyinkcli.

Orchestrates rendering, input handling, and lifecycle management.
"""

from __future__ import annotations

import codecs
import os
import signal
import sys
import threading
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    TextIO,
)

from pyinkcli._component_runtime import createElement, scopeRender
from pyinkcli.components._accessibility_runtime import _provide_accessibility
from pyinkcli.components._app_context_runtime import Props as AppContextProps
from pyinkcli.hooks._runtime import (
    _clear_hook_state,
    _flush_scheduled_rerender,
    _reset_hook_state,
    _set_rerender_callback,
)
from pyinkcli.hooks.use_app import _set_app_ink
from pyinkcli.hooks.use_input import _clear_input_handlers, _dispatch_input
from pyinkcli.hooks.use_stderr import _set_stderr
from pyinkcli.hooks.use_stdin import _set_stdin, useStdin
from pyinkcli.hooks.use_stdout import _emit_stdout_resize, _set_stdout
from pyinkcli.input_parser import InputParser
from pyinkcli.instances import instances
from pyinkcli.log_update import LogUpdate
from pyinkcli.packages.ink.dom import DOMElement, createNode
from pyinkcli.packages.ink.host_config import ReconcilerHostConfig
from pyinkcli.packages.ink.renderer import RenderResult
from pyinkcli.packages.ink.renderer import render as render_dom
from pyinkcli.packages.react_reconciler.ReactFiberReconciler import createReconciler
from pyinkcli.patch_console import patch_console
from pyinkcli.sanitize_ansi import sanitizeAnsi
from pyinkcli.utils import getWindowSize
from pyinkcli.utils.ansi_escapes import (
    begin_synchronized_output,
    clear_terminal,
    cursor_hide,
    cursor_show,
    end_synchronized_output,
    enter_alternative_screen,
    exit_alternative_screen,
)
from pyinkcli.write_synchronized import shouldSynchronize

if TYPE_CHECKING:
    from pyinkcli.component import RenderableNode


def _create_root_node() -> DOMElement:
    root = createNode("ink-root")
    return root


@dataclass
class RenderMetrics:
    """Performance metrics for a render operation."""

    render_time: float


@dataclass
class Options:
    """Options for the Ink application."""

    stdout: TextIO = None  # type: ignore
    stdin: TextIO = None  # type: ignore
    stderr: TextIO = None  # type: ignore
    debug: bool = False
    exit_on_ctrl_c: bool = True
    patch_console: bool = True
    is_screen_reader_enabled: bool | None = None
    wait_until_exit: Callable[[], Any] | None = None
    max_fps: int = 30
    incremental_rendering: bool = False
    concurrent: bool = False
    kitty_keyboard: dict[str, Any] | None = None
    interactive: bool | None = None
    alternate_screen: bool = False
    on_render: Callable[[RenderMetrics], None] | None = None



class Ink:
    """
    Main Ink application class.

    Manages rendering, input handling, and application lifecycle.
    """

    @staticmethod
    def _throttle(func, wait: int):
        last_call = [0.0]
        pending = [False]

        def throttled():
            now = time.time() * 1000
            remaining = wait - (now - last_call[0])

            if remaining <= 0:
                last_call[0] = now
                func()
                pending[0] = False
                return

            if pending[0]:
                return

            pending[0] = True

            def later():
                time.sleep(remaining / 1000)
                last_call[0] = time.time() * 1000
                func()
                pending[0] = False

            threading.Thread(target=later, daemon=True).start()

        return throttled

    @staticmethod
    def _resolve_interactive(stdout: TextIO, interactive: bool | None) -> bool:
        if interactive is not None:
            return interactive

        is_tty = stdout.isatty() if hasattr(stdout, "isatty") else False
        is_ci = os.environ.get("CI", "").lower() in ("true", "1")
        return is_tty and not is_ci

    @classmethod
    def mount(
        cls,
        node: RenderableNode | Callable,
        *,
        stdout: TextIO,
        stdin: TextIO,
        stderr: TextIO,
        **kwargs: Any,
    ) -> Ink:
        """Create or reuse a render instance for a target stdout stream."""
        stream_key = id(stdout)
        existing = instances.get(stream_key)
        if isinstance(existing, cls) and not getattr(existing, "_is_unmounted", False):
            existing.render(node)
            return existing

        options = Options(
            stdout=stdout,
            stdin=stdin,
            stderr=stderr,
            **kwargs,
        )
        app = cls(options)
        app._register_on_unmount(lambda: instances.pop(stream_key, None))
        app.render(node)
        instances[stream_key] = app
        return app

    def __init__(self, options: Options | None = None):
        """
        Initialize the Ink application.

        Args:
            options: Application options.
        """
        options = options or Options()

        # Set defaults for streams
        self._stdout = options.stdout or sys.stdout
        self._stdin = options.stdin or sys.stdin
        self._stderr = options.stderr or sys.stderr

        self._debug = options.debug
        self._exit_on_ctrl_c = options.exit_on_ctrl_c
        self._max_fps = options.max_fps
        self._concurrent = options.concurrent
        self._on_render = options.on_render
        self._interactive = self._resolve_interactive(
            self._stdout,
            options.interactive,
        )
        self._alternate_screen = False
        self._requested_alternate_screen = options.alternate_screen
        self._is_screen_reader_enabled = (
            options.is_screen_reader_enabled
            or os.environ.get("INK_SCREEN_READER", "").lower() == "true"
        )

        # State
        self._is_unmounted = False
        self._is_unmounting = False
        self._last_output = ""
        self._last_output_to_render = ""
        self._last_output_height = 0
        self._last_static_output_frame = ""
        self._last_terminal_width = getWindowSize(self._stdout)["columns"]
        self._current_component: RenderableNode | Callable | None = None
        self._full_static_output = ""
        self._has_pending_throttled_render = False
        self._pending_commit_priority = "default"

        # Exit handling
        self._exit_promise: threading.Event = threading.Event()
        self._render_flush_event: threading.Event = threading.Event()
        self._render_flush_event.set()
        self._transition_idle_event: threading.Event = threading.Event()
        self._transition_idle_event.set()
        self._exit_result: Any = None
        self._exit_error: Exception | None = None
        self._before_exit_handler: Callable[[], None] | None = None
        self._on_unmount_callbacks: list[Callable[[], None]] = []
        self._transition_generation = 0
        self._transition_lock = threading.Lock()
        self._restore_console: Callable[[], None] | None = None
        self._stdin_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")

        # Create root node
        self._root_node = _create_root_node()

        # Set up render throttling
        render_throttle_ms = (
            max(1, int(1000 / self._max_fps)) if self._max_fps > 0 else 0
        )
        if not (self._debug or self._is_screen_reader_enabled):
            self._throttled_render = self._throttle(
                self._on_render_callback,
                render_throttle_ms,
            )

        # Create log update
        self._log = LogUpdate(
            self._stdout,
            incremental=options.incremental_rendering,
        )

        # Create reconciler
        self._reconciler = createReconciler(self._root_node)
        self._reconciler.configure_host(
            ReconcilerHostConfig(
                get_current_component=lambda: (
                    None if self._is_unmounted else self._current_component
                ),
                perform_render=self.render,
                wait_for_render_flush=self._wait_for_render_flush,
                request_render=self._request_commit_render,
            )
        )
        self._container = self._reconciler.create_container(
            self._root_node,
            tag=1 if self._concurrent else 0,
        )
        self._root_node.onComputeLayout = self._calculate_layout
        self._root_node.onRender = self._handle_root_render
        self._root_node.onImmediateRender = self._handle_root_immediate_render

        # Set up app context
        self._app_context = AppContextProps(self)
        self._app_context.stdin = self._stdin
        self._app_context.stdout = self._stdout
        self._app_context.stderr = self._stderr
        self._app_context.exit_on_ctrl_c = self._exit_on_ctrl_c
        self._app_context.interactive = self._interactive
        self._app_context.write_to_stdout = self._write_to_stdout
        self._app_context.write_to_stderr = self._write_to_stderr
        self._app_context.set_cursor_position = self.set_cursor_position
        self._app_context.schedule_transition = self._schedule_transition
        self._app_context.on_exit = self._handle_app_exit

        # Set app handle
        _set_app_ink(self)
        _set_stdin(self._stdin, self._stdout)
        _set_stdout(self._stdout)
        _set_stderr(self._stderr)
        _set_rerender_callback(self._rerender)

        # Set up exit signal handler
        self._setup_exit_handler()

        # Set up alternate screen
        self._set_alternate_screen(self._requested_alternate_screen)

        if os.environ.get("DEV", "").lower() == "true":
            self._reconciler.injectIntoDevTools()

        if options.patch_console and not self._debug:
            self._patch_console()

        # Set up resize handler
        if self._interactive:
            self._setup_resize_handler()

        # Set up input handling
        self._setup_input_handler()

    @property
    def is_concurrent(self) -> bool:
        """Check if concurrent rendering mode is enabled."""
        return self._concurrent

    def render(self, node: RenderableNode | Callable) -> None:
        """
        Render a component tree.

        Args:
            node: The root component or virtual node to render.
        """
        if self._is_unmounted:
            return

        self._render_flush_event.clear()

        self._current_component = node
        vnode = self._normalize_render_node(node)
        wrapped = self._create_wrapped_app(vnode)

        # Set context
        _reset_hook_state()
        self._reconciler.submit_container(
            wrapped,
            self._container,
        )

        if not self._container.rerender_running:
            self._drain_pending_hook_rerenders()

    def _normalize_render_node(
        self,
        node: RenderableNode | Callable,
    ) -> RenderableNode:
        if callable(node):
            return createElement(node)
        if isinstance(node, str):
            return createElement("ink-text", node)
        return node

    def _create_wrapped_app(self, vnode: RenderableNode) -> RenderableNode:
        from pyinkcli.components.App import App

        return scopeRender(
            createElement(
                App,
                vnode,
                app_context=self._app_context,
                stdin=self._stdin,
                stdout=self._stdout,
                stderr=self._stderr,
                exit_on_ctrl_c=self._exit_on_ctrl_c,
                interactive=self._interactive,
                debug=self._debug,
                write_to_stdout=self._write_to_stdout,
                write_to_stderr=self._write_to_stderr,
                set_cursor_position=self.set_cursor_position,
                on_exit=self._handle_app_exit,
            ),
            lambda: _provide_accessibility(self._is_screen_reader_enabled),
        )

    def unmount(self, error: Exception | None = None) -> None:
        """
        Unmount the application.

        Args:
            error: Optional error that caused unmount.
        """
        if self._is_unmounted or self._is_unmounting:
            return

        self._is_unmounting = True

        self._invoke_before_exit_handler()
        self._perform_final_render()

        self._is_unmounted = True
        self._restore_console_if_needed()
        self._cleanup()
        self._finalize_exit_state(error)

    def wait_until_exit(self) -> Any:
        """
        Wait for the application to exit.

        Returns:
            The exit result if any.
        """
        if not self._before_exit_handler:

            def before_exit():
                self.unmount()

            self._before_exit_handler = before_exit

        self._exit_promise.wait()
        if self._exit_error:
            raise self._exit_error
        return self._exit_result

    def wait_until_render_flush(self, timeout: float | None = None) -> None:
        """Wait until the latest render has been written out."""
        if self._is_unmounted or self._is_unmounting:
            return

        _flush_scheduled_rerender()
        self._wait_for_render_flush(timeout=timeout)
        self._wait_for_transition_idle(timeout=timeout)

    def rerender(self, node: RenderableNode | Callable) -> None:
        """Alias matching the JS Instance surface."""
        self.render(node)

    def cleanup(self) -> None:
        """Compatibility alias for unmount()."""
        self.unmount()

    def _register_on_unmount(self, callback: Callable[[], None]) -> None:
        """Register a callback invoked exactly once during unmount cleanup."""
        self._on_unmount_callbacks.append(callback)

    def _invoke_before_exit_handler(self) -> None:
        if self._before_exit_handler:
            with suppress(Exception):
                self._before_exit_handler()

    def _perform_final_render(self) -> None:
        if not self._should_perform_final_render():
            return
        try:
            self._calculate_layout()
            self._on_render_callback()
        except AssertionError:
            # Yoga can transiently assert during signal-driven teardown if background
            # updates race with final unmount. JS Ink exits without a final frame in
            # that case; skipping the final render keeps teardown robust.
            return

    def _finalize_exit_state(self, error: Exception | None) -> None:
        if error:
            self._exit_error = error
        self._mark_transition_idle()
        self._mark_render_flushed()
        self._exit_promise.set()

    def clear(self) -> None:
        """Clear the terminal output."""
        if self._can_clear_terminal_output():
            self._clear_and_restore_output()

    def set_cursor_position(self, position: tuple[int, int] | None) -> None:
        """Set the cursor position relative to the current Ink output."""
        self._set_log_cursor_position(position)

    def _on_render_callback(self) -> None:
        """Handle render callback from reconciler."""
        self._has_pending_throttled_render = False

        if self._is_unmounted:
            return

        if self._on_render:
            start_time = time.perf_counter()
            result = self._sanitize_render_result(
                render_dom(self._root_node, self._is_screen_reader_enabled)
            )
            metrics = RenderMetrics(render_time=time.perf_counter() - start_time)
            self._on_render(metrics)
        else:
            result = self._sanitize_render_result(
                render_dom(self._root_node, self._is_screen_reader_enabled)
            )

        static_output_delta = self._get_static_output_delta(result.staticOutput)
        has_static_output = static_output_delta != ""
        self._last_static_output_frame = result.staticOutput

        self._render_frame(
            result.output,
            result.outputHeight,
            static_output_delta if has_static_output else "",
        )

        self._mark_render_flushed()

    def _sanitize_render_result(self, result: RenderResult) -> RenderResult:
        # Final render-result sanitization is the outermost defense layer.
        # Even if a deeper render path regresses, debug/static composition
        # should not write raw user control sequences straight to the terminal.
        return RenderResult(
            output=sanitizeAnsi(result.output),
            outputHeight=result.outputHeight,
            staticOutput=sanitizeAnsi(result.staticOutput),
        )

    def _mark_render_flushed(self) -> None:
        self._render_flush_event.set()

    def _mark_transition_idle(self) -> None:
        self._transition_idle_event.set()

    def _wait_for_render_flush(self, timeout: float | None = None) -> None:
        self._render_flush_event.wait(timeout=timeout)

    def _wait_for_transition_idle(self, timeout: float | None = None) -> None:
        self._transition_idle_event.wait(timeout=timeout)

    def _can_clear_terminal_output(self) -> bool:
        return self._interactive and not self._debug

    def _set_log_cursor_position(self, position: tuple[int, int] | None) -> None:
        self._log.set_cursor_position(position)

    def _should_perform_final_render(self) -> bool:
        if self._is_stdout_closed():
            return False

        return not (not self._interactive and self._last_output)

    def _render_frame(
        self,
        output: str,
        output_height: int,
        static_output: str,
    ) -> None:
        if self._debug:
            self._render_debug_frame(output, output_height, static_output)
            return

        if not self._interactive:
            self._render_non_interactive_frame(output, output_height, static_output)
            return

        self._append_static_output(static_output)
        self._render_interactive_frame(output, output_height, static_output)

    def _append_static_output(self, static_output: str) -> None:
        if static_output:
            self._full_static_output += static_output

    def _render_debug_frame(
        self,
        output: str,
        output_height: int,
        static_output: str,
    ) -> None:
        self._append_static_output(static_output)
        self._last_output = output
        self._last_output_to_render = output
        self._last_output_height = output_height
        self._write_stream(self._stdout, self._full_static_output + output)

    def _render_non_interactive_frame(
        self,
        output: str,
        output_height: int,
        static_output: str,
    ) -> None:
        if static_output:
            self._append_static_output(static_output)
            self._write_stream(self._stdout, static_output)
        self._last_output = output
        self._last_output_to_render = output + "\n"
        self._last_output_height = output_height

    def _get_static_output_delta(self, static_output: str) -> str:
        """Return only the newly produced portion of static output."""
        if not static_output or static_output == "\n":
            return ""

        previous_frame = self._last_static_output_frame
        if previous_frame and static_output.startswith(previous_frame):
            return static_output[len(previous_frame):]

        if static_output == previous_frame:
            return ""

        return static_output

    def _render_interactive_frame(
        self,
        output: str,
        output_height: int,
        static_output: str,
    ) -> None:
        """Render an interactive frame."""
        has_static_output = static_output != ""
        is_tty = self._stdout.isatty() if hasattr(self._stdout, "isatty") else False

        viewport_rows = self._get_viewport_rows(is_tty)
        output_to_render = self._get_output_to_render(output, output_height, is_tty, viewport_rows)

        if self._should_clear_terminal(
            is_tty,
            viewport_rows,
            output_height,
        ):
            self._render_cleared_frame(output, output_height, output_to_render)
            return

        if has_static_output:
            self._render_interactive_static_frame(static_output, output_to_render)
        else:
            self._write_interactive_output(output, output_to_render)

        self._update_last_frame(output, output_to_render, output_height)

    def _write_interactive_output(self, output: str, output_to_render: str) -> None:
        if output == self._last_output and not self._log.is_cursor_dirty():
            return

        self._with_synchronized_stdout(lambda: self._log(output_to_render))

    def _get_viewport_rows(self, is_tty: bool) -> int:
        return getWindowSize(self._stdout)["rows"] if is_tty else 24

    def _get_output_to_render(
        self,
        output: str,
        output_height: int,
        is_tty: bool,
        viewport_rows: int,
    ) -> str:
        is_fullscreen = is_tty and output_height >= viewport_rows
        return output if is_fullscreen else output + "\n"

    def _update_last_frame(
        self,
        output: str,
        output_to_render: str,
        output_height: int,
    ) -> None:
        self._last_output = output
        self._last_output_to_render = output_to_render
        self._last_output_height = output_height

    def _render_cleared_frame(
        self,
        output: str,
        output_height: int,
        output_to_render: str,
    ) -> None:
        def write() -> None:
            self._write_stream(
                self._stdout,
                clear_terminal() + self._full_static_output + output,
            )
            self._update_last_frame(output, output_to_render, output_height)
            self._log.sync(output_to_render)

        self._with_synchronized_stdout(write)

    def _render_interactive_static_frame(
        self,
        static_output: str,
        output_to_render: str,
    ) -> None:
        def write() -> None:
            self._log.clear()
            self._write_stream(self._stdout, static_output)
            self._log(output_to_render)

        self._with_synchronized_stdout(write)

    def _should_clear_terminal(
        self,
        is_tty: bool,
        viewport_rows: int,
        output_height: int,
    ) -> bool:
        """Determine if the terminal should be cleared."""
        if not is_tty:
            return False

        had_previous_frame = self._last_output_height > 0
        was_fullscreen = self._last_output_height >= viewport_rows
        was_overflowing = self._last_output_height > viewport_rows
        is_overflowing = output_height > viewport_rows
        is_leaving_fullscreen = was_fullscreen and output_height < viewport_rows
        should_clear_on_unmount = self._is_unmounting and was_fullscreen
        return (
            was_overflowing
            or (is_overflowing and had_previous_frame)
            or is_leaving_fullscreen
            or should_clear_on_unmount
        )

    def _calculate_layout(self) -> None:
        """Calculate Yoga layout."""
        from pyinkcli import _yoga as yoga

        terminal_width = getWindowSize(self._stdout)["columns"]

        if self._root_node.yogaNode:
            self._root_node.yogaNode.set_width(terminal_width)
            self._root_node.yogaNode.calculate_layout(
                yoga.UNDEFINED,
                yoga.UNDEFINED,
                yoga.DIRECTION_LTR,
            )

    def _rerender(self) -> None:
        """Re-render the current component tree."""
        self._drain_pending_hook_rerenders()

    def _drain_pending_hook_rerenders(self) -> None:
        self._reconciler.drain_pending_rerenders(self._container)

    def _request_commit_render(
        self,
        priority: str,
        immediate: bool,
    ) -> None:
        self._pending_commit_priority = priority
        if immediate and callable(self._root_node.onImmediateRender):
            self._root_node.onImmediateRender()
            return

        if callable(self._root_node.onRender):
            self._root_node.onRender()
            return

        self._flush_requested_root_render(immediate=immediate)

    def _handle_root_render(self) -> None:
        self._flush_requested_root_render(immediate=False)

    def _handle_root_immediate_render(self) -> None:
        self._flush_requested_root_render(immediate=True)

    def _flush_requested_root_render(self, *, immediate: bool) -> None:
        priority = self._pending_commit_priority

        # Keep the first committed frame synchronous. Deferring the initial paint
        # makes PTY-driven apps appear blank until a later event loop turn.
        if (
            immediate
            or self._debug
            or self._is_screen_reader_enabled
            or not self._interactive
            or self._last_output_height == 0
        ):
            self._on_render_callback()
            return

        if priority == "discrete":
            self._on_render_callback()
            return

        self._schedule_throttled_render()

    def _schedule_throttled_render(self) -> None:
        self._has_pending_throttled_render = True
        self._throttled_render()

    def _schedule_transition(
        self,
        callback: Callable[[], None],
        on_complete: Callable[[bool], None] | None = None,
        delay: float = 0.05,
    ) -> None:
        """Schedule a deferred transition callback through the app runtime."""
        if self._is_unmounted or self._is_unmounting:
            if on_complete is not None:
                on_complete(False)
            return

        current_generation = self._begin_transition()

        def run() -> None:
            is_latest = False
            try:
                time.sleep(delay)
                is_latest = self._is_active_transition(current_generation)

                if is_latest:
                    callback()
            finally:
                if on_complete is not None:
                    on_complete(is_latest)
                self._finish_transition(is_latest)

        self._start_background_thread(run)

    def _begin_transition(self) -> int:
        with self._transition_lock:
            self._transition_generation += 1
            self._transition_idle_event.clear()
            return self._transition_generation

    def _is_active_transition(self, generation: int) -> bool:
        with self._transition_lock:
            return (
                not self._is_unmounted
                and not self._is_unmounting
                and generation == self._transition_generation
            )

    def _finish_transition(self, is_latest: bool) -> None:
        if is_latest:
            self._transition_idle_event.set()

    def _start_background_thread(self, target: Callable[[], None]) -> None:
        thread = threading.Thread(target=target, daemon=True)
        thread.start()

    def _handle_app_exit(self, error_or_result: Any = None) -> None:
        """Handle app exit from context."""
        if self._is_unmounted or self._is_unmounting:
            return

        if isinstance(error_or_result, Exception):
            self.unmount(error_or_result)
            return

        self._exit_result = error_or_result
        self.unmount()

    def _with_synchronized_stdout(self, callback: Callable[[], None]) -> None:
        sync = shouldSynchronize(self._stdout, self._interactive)
        if sync:
            self._write_stream(self._stdout, begin_synchronized_output())
        try:
            callback()
        finally:
            if sync:
                self._write_stream(self._stdout, end_synchronized_output())

    def _prepare_stream_payload(self, stream: TextIO, data: str) -> str:
        is_tty = stream.isatty() if hasattr(stream, "isatty") else False
        if not is_tty or not data:
            return data

        return data.replace("\r\n", "\n").replace("\n", "\r\n")

    def _write_stream(self, stream: TextIO, data: str) -> None:
        stream.write(self._prepare_stream_payload(stream, data))

    def _restore_rendered_output(self) -> None:
        self._log(self._get_rendered_output())

    def _clear_and_restore_output(self) -> None:
        self._log.clear()
        self._log.sync(self._get_rendered_output())

    def _get_rendered_output(self) -> str:
        return self._last_output_to_render or self._last_output + "\n"

    def _is_stdout_closed(self) -> bool:
        return hasattr(self._stdout, "closed") and self._stdout.closed

    def _write_debug_overlay(self, stream: TextIO, data: str) -> None:
        if stream is self._stderr:
            self._write_stream(stream, data)
            self._write_stream(self._stdout, self._full_static_output + self._last_output)
        else:
            self._write_stream(
                self._stdout,
                data + self._full_static_output + self._last_output,
            )

    def _write_non_interactive(self, stream: TextIO, data: str) -> None:
        self._write_stream(stream, data)

    def _write_interactive_overlay(self, stream: TextIO, data: str) -> None:
        def write() -> None:
            self._log.clear()
            self._write_stream(stream, data)
            self._restore_rendered_output()

        self._with_synchronized_stdout(write)

    def _dispatch_overlay_write(self, stream: TextIO, data: str) -> None:
        if self._is_unmounted:
            return

        data = sanitizeAnsi(data)

        if self._debug:
            self._write_debug_overlay(stream, data)
            return

        if not self._interactive:
            self._write_non_interactive(stream, data)
            return

        self._write_interactive_overlay(stream, data)

    def _write_to_stdout(self, data: str) -> None:
        """Write data to stdout."""
        self._dispatch_overlay_write(self._stdout, data)

    def _write_to_stderr(self, data: str) -> None:
        """Write data to stderr."""
        self._dispatch_overlay_write(self._stderr, data)

    def _patch_console(self) -> None:
        self._restore_console = patch_console(self._handle_patched_console_write)

    def _handle_patched_console_write(self, stream: str, data: str) -> None:
        if stream == "stdout":
            self._write_to_stdout(data)
            return

        if not data.startswith("The above error occurred"):
            self._write_to_stderr(data)

    def _install_signal_handler(
        self,
        signum: int,
        handler: Callable[[int, Any], None],
    ) -> None:
        signal.signal(signum, handler)

    def _setup_exit_handler(self) -> None:
        """Set up signal handlers for exit."""
        def signal_handler(signum, frame):
            self._handle_exit_signal()

        self._install_signal_handler(signal.SIGINT, signal_handler)
        self._install_signal_handler(signal.SIGTERM, signal_handler)

    def _handle_exit_signal(self) -> None:
        self.unmount()

    def _handle_resize(self) -> None:
        current_width = getWindowSize(self._stdout)["columns"]

        if current_width < self._last_terminal_width:
            self._reset_rendered_frame()

        self._last_terminal_width = current_width
        _emit_stdout_resize()

        if self._current_component is not None:
            self.render(self._current_component)
            return

        self._calculate_layout()
        self._on_render_callback()

    def _reset_rendered_frame(self) -> None:
        self._log.clear()
        self._last_output = ""
        self._last_output_to_render = ""

    def _setup_resize_handler(self) -> None:
        """Set up terminal resize handler."""
        def handle_sigwinch(signum, frame):
            self._handle_resize()

        self._install_signal_handler(signal.SIGWINCH, handle_sigwinch)

    def _setup_input_handler(self) -> None:
        """Set up keyboard input handler."""
        if not self._interactive:
            return

        parser = InputParser()
        stdin_handle = useStdin()

        def read_input():
            try:
                while not self._is_unmounted:
                    data = self._read_stdin_chunk()
                    if data:
                        self._dispatch_parser_events(parser.feed(data), stdin_handle)

                self._dispatch_parser_events(parser.flush(), stdin_handle)
            except Exception:
                pass

        self._start_background_thread(read_input)

    def _read_stdin_chunk(self) -> str:
        if hasattr(self._stdin, "buffer"):
            while True:
                chunk = self._stdin.buffer.read(1)
                if not chunk:
                    return self._stdin_decoder.decode(b"", final=True)

                decoded = self._stdin_decoder.decode(chunk, final=False)
                if decoded:
                    return decoded

        return self._stdin.read(1)

    def _dispatch_parser_events(self, events: Any, stdin_handle: Any) -> None:
        for event in events:
            if event.kind == "paste":
                if stdin_handle.listener_count("paste") == 0:
                    _dispatch_input(event.data)
                else:
                    stdin_handle.emit("paste", event.data)
            else:
                _dispatch_input(event.data)

    def _set_alternate_screen(self, enabled: bool) -> None:
        """Set alternate screen mode."""
        self._alternate_screen = self._should_enable_alternate_screen(enabled)
        if self._alternate_screen:
            self._enter_alternate_screen()

    def _should_enable_alternate_screen(self, enabled: bool) -> bool:
        return (
            enabled
            and self._interactive
            and (self._stdout.isatty() if hasattr(self._stdout, "isatty") else False)
        )

    def _enter_alternate_screen(self) -> None:
        self._write_alternate_screen_enter_sequence()
        self._flush_stdout()

    def _write_alternate_screen_enter_sequence(self) -> None:
        self._write_stream(self._stdout, enter_alternative_screen())
        self._write_stream(self._stdout, cursor_hide())

    def _run_unmount_callbacks(self) -> None:
        callbacks = self._on_unmount_callbacks[:]
        self._on_unmount_callbacks.clear()
        for callback in callbacks:
            with suppress(Exception):
                callback()

    def _restore_terminal_state(self) -> None:
        if self._is_stdout_closed():
            return

        if self._alternate_screen:
            self._leave_alternate_screen()

        self._restore_terminal_output_mode()

    def _restore_terminal_output_mode(self) -> None:
        if not self._interactive:
            self._write_stream(self._stdout, self._get_final_non_interactive_output())
        elif not self._debug:
            self._log.done()

    def _leave_alternate_screen(self) -> None:
        self._write_alternate_screen_exit_sequence()
        self._alternate_screen = False

    def _write_alternate_screen_exit_sequence(self) -> None:
        self._write_stream(self._stdout, exit_alternative_screen())
        self._write_stream(self._stdout, cursor_show())

    def _flush_stdout(self) -> None:
        self._stdout.flush()

    def _get_final_non_interactive_output(self) -> str:
        return "\n" if self._debug else self._last_output + "\n"

    def _cleanup(self) -> None:
        """Clean up resources."""
        self._run_unmount_callbacks()

        _set_rerender_callback(None)
        self._reconciler.cleanup_class_component_instances()
        _clear_hook_state()
        _clear_input_handlers()
        self._restore_terminal_state()
        self._flush_stdout()

    def _restore_console_if_needed(self) -> None:
        if self._restore_console is not None:
            self._restore_console()
            self._restore_console = None
