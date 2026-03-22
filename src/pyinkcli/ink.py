from __future__ import annotations

from dataclasses import dataclass
import threading
from types import SimpleNamespace

from .component import createElement
from .hooks import _runtime as hooks_runtime
from .hooks._runtime import _clear_hook_state, _set_rerender_callback, _set_schedule_update_callback
from .hooks.use_app import _set_current_app
from .hooks.use_input import _clear_input_handlers
from .hooks.use_stderr import _StderrHandle, _set_stderr_handle
from .hooks.use_stdout import _StdoutHandle, _set_stdout_handle
from .hooks.use_window_size import _set_window_size
from .packages.react_reconciler.ReactFiberWorkLoop import flushPendingEffects
from .reconciler import createReconciler
from .render_node_to_output import renderNodeToOutput, renderNodeToScreenReaderOutput
from .render_to_string import create_root_node
from .suspense_runtime import _set_renderer_rerender
from .utils.ansi_escapes import enter_alternative_screen, exit_alternative_screen, hide_cursor_escape


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
        self._log = SimpleNamespace(_cursor_position=(0, 0))
        hooks_runtime._dirty_components.clear()
        hooks_runtime._render_phase_rerender_count = 0
        self._root_node = create_root_node(
            getattr(self.stdout, "columns", 80),
            getattr(self.stdout, "rows", 24),
        )
        self._root_node.onComputeLayout = lambda: None
        self._root_node.onRender = lambda: None
        self._root_node.onImmediateRender = lambda: None
        self._reconciler = createReconciler(self._root_node)
        self._container = self._reconciler.create_container(self._root_node, tag=1 if options.concurrent else 0)
        self.rerender = self._rerender_explicit
        self.cleanup = self.unmount
        _set_current_app(self)
        _set_rerender_callback(self._rerender_current)
        _set_schedule_update_callback(lambda fiber, priority: self._rerender_current())
        _set_renderer_rerender(self._rerender_current)
        _set_stdout_handle(_StdoutHandle(self.stdout))
        _set_stderr_handle(_StderrHandle(self.stderr))
        _set_window_size(
            getattr(self.stdout, "columns", 80),
            getattr(self.stdout, "rows", 24),
        )
        if options.alternate_screen and options.interactive:
            self._write_stream(self.stdout, enter_alternative_screen() + hide_cursor_escape)

    def render(self, node) -> None:
        self._current_node = createElement(node) if callable(node) and not getattr(node, "type", None) else node
        self._reconciler.update_container(self._current_node, self._container)
        if self.options.concurrent and getattr(self._container, "scheduled_timer", None) is not None:
            return
        self._rendered_output = self._render_output()
        if self._can_rewrite_stream(self.stdout):
            self.stdout.seek(0)
            self.stdout.truncate(0)
        self._write_stream(self.stdout, self._rendered_output)

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
                self.render(self._current_node)
            finally:
                self._reconciler._force_rerender = False

    def unmount(self) -> None:
        if self._is_unmounted:
            return
        self._is_unmounted = True
        _clear_input_handlers()
        _clear_hook_state()
        _set_rerender_callback(None)
        _set_schedule_update_callback(None)
        if self.options.alternate_screen and self.options.interactive:
            self._write_stream(self.stdout, exit_alternative_screen())

    def wait_until_exit(self, timeout: float | None = None):
        self.wait_until_render_flush(timeout or 0.3)
        return None

    def wait_until_render_flush(self, timeout: float | None = None):
        if getattr(self._container, "scheduled_timer", None) is not None:
            try:
                self._container.scheduled_timer.join(timeout or 0.1)
            except RuntimeError:
                pass
            self._container.scheduled_timer = None
        for timer in list(self._transition_threads):
            try:
                timer.join(timeout or 0.1)
            except RuntimeError:
                pass
        auto_batch_timer = getattr(hooks_runtime, "_auto_batch_timer", None)
        if auto_batch_timer is not None:
            try:
                auto_batch_timer.join(timeout or 0.1)
            except RuntimeError:
                pass
        flushPendingEffects()
        if getattr(hooks_runtime, "_dirty_components", None):
            self._reconciler._force_rerender = True
            try:
                self.render(self._current_node)
            finally:
                self._reconciler._force_rerender = False
            hooks_runtime._dirty_components.clear()
        if self._current_node is not None and not self._is_unmounted:
            self._rendered_output = self._render_output()
            if self._can_rewrite_stream(self.stdout):
                self.stdout.seek(0)
                self.stdout.truncate(0)
            self._write_stream(self.stdout, self._rendered_output)
        hooks_runtime._dirty_components.clear()
        if getattr(self._container, "scheduled_timer", None) is None:
            self._container.render_state = None
        return None

    def clear(self) -> None:
        if self._can_rewrite_stream(self.stdout):
            self.stdout.seek(0)
            self.stdout.truncate(0)

    def _can_rewrite_stream(self, stream) -> bool:
        if not (hasattr(stream, "seek") and hasattr(stream, "truncate")):
            return False
        try:
            return bool(stream.seekable())
        except Exception:  # noqa: BLE001
            return False

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
        self.stdout.write(self._prepare_stream_payload(self.stdout, text) + self._rendered_output)

    def _write_to_stderr(self, text: str) -> None:
        self.stderr.write(self._prepare_stream_payload(self.stderr, text))

    def _handle_resize(self) -> None:
        self._root_node.width = getattr(self.stdout, "columns", 80)
        self._root_node.height = getattr(self.stdout, "rows", 24)
        _set_window_size(self._root_node.width, self._root_node.height)
        self._rerender_current()

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
        if self.options.screen_reader_enabled:
            return renderNodeToScreenReaderOutput(self._root_node)
        return renderNodeToOutput(self._root_node)


__all__ = ["Ink", "Options"]
