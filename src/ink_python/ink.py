"""
Main Ink class for ink-python.

Orchestrates rendering, input handling, and lifecycle management.
"""

from __future__ import annotations

import os
import shutil
import signal
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    TextIO,
    Union,
)

from ink_python.component import VNode, create_vnode
from ink_python.context import AppContext, provide_app_context, provide_stdin, provide_stdout, provide_stderr
from ink_python.dom import DOMElement, create_node
from ink_python.hooks.use_app import _set_app_ink
from ink_python.hooks.use_input import _dispatch_input, _clear_input_handlers
from ink_python.hooks.state import _reset_hook_state, _set_rerender_callback
from ink_python.reconciler import Reconciler, create_reconciler
from ink_python.renderer import render as render_dom, RenderResult
from ink_python.log_update import LogUpdate
from ink_python.utils.ansi_escapes import (
    cursor_hide,
    cursor_show,
    enter_alternative_screen,
    exit_alternative_screen,
    erase_lines,
    clear_terminal,
    begin_synchronized_output,
    end_synchronized_output,
)


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
    is_screen_reader_enabled: Optional[bool] = None
    wait_until_exit: Optional[Callable[[], Any]] = None
    max_fps: int = 30
    incremental_rendering: bool = False
    concurrent: bool = False
    kitty_keyboard: Optional[Dict[str, Any]] = None
    interactive: Optional[bool] = None
    alternate_screen: bool = False
    on_render: Optional[Callable[[RenderMetrics], None]] = None


class Ink:
    """
    Main Ink application class.

    Manages rendering, input handling, and application lifecycle.
    """

    def __init__(self, options: Optional[Options] = None):
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
        self._on_render = options.on_render
        self._interactive = self._resolve_interactive(options.interactive)
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
        self._last_terminal_width = self._get_window_size()[0]
        self._current_component: Optional[Union[VNode, Callable, str]] = None
        self._full_static_output = ""
        self._has_pending_throttled_render = False

        # Exit handling
        self._exit_promise: threading.Event = threading.Event()
        self._exit_result: Any = None
        self._exit_error: Optional[Exception] = None
        self._before_exit_handler: Optional[Callable[[], None]] = None

        # Create root node
        self._root_node = create_node("ink-root")
        self._root_node.on_compute_layout = self._calculate_layout

        # Set up render throttling
        render_throttle_ms = (
            max(1, int(1000 / self._max_fps)) if self._max_fps > 0 else 0
        )
        if self._debug or self._is_screen_reader_enabled:
            self._root_node.on_render = self._on_render_callback
        else:
            self._throttled_render = _throttle(
                self._on_render_callback,
                render_throttle_ms,
            )
            self._root_node.on_render = lambda: (
                setattr(self, "_has_pending_throttled_render", True),
                self._throttled_render(),
            )

        self._root_node.on_immediate_render = self._on_render_callback

        # Create log update
        self._log = LogUpdate(
            self._stdout,
            incremental=options.incremental_rendering,
        )

        # Create reconciler
        self._reconciler = create_reconciler(self._root_node)
        self._container = self._reconciler.create_container(self._root_node)

        # Set up app context
        self._app_context = AppContext(self)
        self._app_context.stdin = self._stdin
        self._app_context.stdout = self._stdout
        self._app_context.stderr = self._stderr
        self._app_context.exit_on_ctrl_c = self._exit_on_ctrl_c
        self._app_context.interactive = self._interactive
        self._app_context.write_to_stdout = self._write_to_stdout
        self._app_context.write_to_stderr = self._write_to_stderr
        self._app_context.on_exit = self._handle_app_exit

        # Set app handle
        _set_app_ink(self)
        _set_rerender_callback(self._rerender)

        # Set up exit signal handler
        self._setup_exit_handler()

        # Set up alternate screen
        self._set_alternate_screen(self._requested_alternate_screen)

        # Set up resize handler
        if self._interactive:
            self._setup_resize_handler()

        # Set up input handling
        self._setup_input_handler()

    @property
    def is_concurrent(self) -> bool:
        """Check if concurrent rendering mode is enabled."""
        return False  # Simplified for now

    def render(self, node: Union[VNode, Callable, str]) -> None:
        """
        Render a component tree.

        Args:
            node: The root component or VNode to render.
        """
        if self._is_unmounted:
            return

        # Convert to VNode if needed
        self._current_component = node
        if callable(node):
            vnode = node()
        elif isinstance(node, str):
            vnode = create_vnode("ink-text", node)
        else:
            vnode = node

        # Wrap with App context
        from ink_python.components.app import App

        wrapped = create_vnode(
            App,
            vnode,
            stdin=self._stdin,
            stdout=self._stdout,
            stderr=self._stderr,
            exit_on_ctrl_c=self._exit_on_ctrl_c,
            interactive=self._interactive,
            write_to_stdout=self._write_to_stdout,
            write_to_stderr=self._write_to_stderr,
            on_exit=self._handle_app_exit,
        )

        # Reset hook state
        _reset_hook_state()

        # Set context
        with provide_app_context(self._app_context):
            with provide_stdin(self._stdin):
                with provide_stdout(self._stdout):
                    with provide_stderr(self._stderr):
                        # Update container
                        self._reconciler.update_container(
                            wrapped,
                            self._container,
                        )

    def unmount(self, error: Optional[Exception] = None) -> None:
        """
        Unmount the application.

        Args:
            error: Optional error that caused unmount.
        """
        if self._is_unmounted or self._is_unmounting:
            return

        self._is_unmounting = True

        # Run before exit handler
        if self._before_exit_handler:
            try:
                self._before_exit_handler()
            except Exception:
                pass

        # Calculate layout and render one last time
        if self._can_write():
            self._calculate_layout()
            self._on_render_callback()

        self._is_unmounted = True

        # Clean up
        self._cleanup()

        # Resolve exit promise
        if error:
            self._exit_error = error
        self._exit_promise.set()

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

    def clear(self) -> None:
        """Clear the terminal output."""
        if self._interactive and not self._debug:
            self._log.clear()
            self._log.sync(self._last_output_to_render or self._last_output + "\n")

    def _on_render_callback(self) -> None:
        """Handle render callback from reconciler."""
        self._has_pending_throttled_render = False

        if self._is_unmounted:
            return

        start_time = time.time()
        result = render_dom(self._root_node, self._is_screen_reader_enabled)

        if self._on_render:
            metrics = RenderMetrics(render_time=time.time() - start_time)
            self._on_render(metrics)

        has_static_output = result.static_output and result.static_output != "\n"

        if self._debug:
            if has_static_output:
                self._full_static_output += result.static_output
            self._last_output = result.output
            self._last_output_to_render = result.output
            self._last_output_height = result.output_height
            self._stdout.write(self._full_static_output + result.output)
            return

        if not self._interactive:
            if has_static_output:
                self._stdout.write(result.static_output)
            self._last_output = result.output
            self._last_output_to_render = result.output + "\n"
            self._last_output_height = result.output_height
            return

        if has_static_output:
            self._full_static_output += result.static_output

        self._render_interactive_frame(
            result.output,
            result.output_height,
            result.static_output if has_static_output else "",
        )

    def _render_interactive_frame(
        self,
        output: str,
        output_height: int,
        static_output: str,
    ) -> None:
        """Render an interactive frame."""
        has_static_output = static_output != ""
        is_tty = self._stdout.isatty() if hasattr(self._stdout, "isatty") else False

        # Determine output to render
        viewport_rows = (
            self._get_window_size()[1]
            if is_tty
            else 24
        )
        is_fullscreen = is_tty and output_height >= viewport_rows
        output_to_render = output if is_fullscreen else output + "\n"

        # Check if we should clear terminal
        should_clear = self._should_clear_terminal(
            is_tty,
            viewport_rows,
            output_height,
        )

        if should_clear:
            sync = self._should_sync()
            if sync:
                self._stdout.write(begin_synchronized_output())

            self._stdout.write(
                clear_terminal()
                + self._full_static_output
                + output
            )
            self._last_output = output
            self._last_output_to_render = output_to_render
            self._last_output_height = output_height
            self._log.sync(output_to_render)

            if sync:
                self._stdout.write(end_synchronized_output())

            return

        # Render with static output handling
        if has_static_output:
            sync = self._should_sync()
            if sync:
                self._stdout.write(begin_synchronized_output())

            self._log.clear()
            self._stdout.write(static_output)
            self._log(output_to_render)

            if sync:
                self._stdout.write(end_synchronized_output())
        elif output != self._last_output:
            self._log(output_to_render)

        self._last_output = output
        self._last_output_to_render = output_to_render
        self._last_output_height = output_height

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
        is_leaving_fullscreen = (
            was_fullscreen and output_height < viewport_rows
        )
        should_clear_on_unmount = self._is_unmounting and was_fullscreen

        return (
            was_overflowing
            or (is_overflowing and had_previous_frame)
            or is_leaving_fullscreen
            or should_clear_on_unmount
        )

    def _calculate_layout(self) -> None:
        """Calculate Yoga layout."""
        from ink_python import yoga_compat as yoga

        terminal_width = self._get_window_size()[0]

        if self._root_node.yoga_node:
            self._root_node.yoga_node.set_width(terminal_width)
            self._root_node.yoga_node.calculate_layout(
                yoga.UNDEFINED,
                yoga.UNDEFINED,
                yoga.DIRECTION_LTR,
            )

    def _rerender(self) -> None:
        """Re-render the current component tree."""
        if self._is_unmounted or self._current_component is None:
            return

        self.render(self._current_component)

    def _handle_app_exit(self, error_or_result: Any = None) -> None:
        """Handle app exit from context."""
        if self._is_unmounted or self._is_unmounting:
            return

        if isinstance(error_or_result, Exception):
            self.unmount(error_or_result)
            return

        self._exit_result = error_or_result
        self.unmount()

    def _write_to_stdout(self, data: str) -> None:
        """Write data to stdout."""
        if self._is_unmounted:
            return

        if self._debug:
            self._stdout.write(data + self._full_static_output + self._last_output)
            return

        if not self._interactive:
            self._stdout.write(data)
            return

        sync = self._should_sync()
        if sync:
            self._stdout.write(begin_synchronized_output())

        self._log.clear()
        self._stdout.write(data)

        # Restore last output
        self._log(self._last_output_to_render or self._last_output + "\n")

        if sync:
            self._stdout.write(end_synchronized_output())

    def _write_to_stderr(self, data: str) -> None:
        """Write data to stderr."""
        if self._is_unmounted:
            return

        if self._debug:
            self._stderr.write(data)
            self._stdout.write(self._full_static_output + self._last_output)
            return

        if not self._interactive:
            self._stderr.write(data)
            return

        sync = self._should_sync()
        if sync:
            self._stdout.write(begin_synchronized_output())

        self._log.clear()
        self._stderr.write(data)

        # Restore last output
        self._log(self._last_output_to_render or self._last_output + "\n")

        if sync:
            self._stdout.write(end_synchronized_output())

    def _resolve_interactive(self, interactive: Optional[bool]) -> bool:
        """Resolve the interactive setting."""
        if interactive is not None:
            return interactive

        # Default: interactive if stdout is a TTY and not in CI
        is_tty = (
            self._stdout.isatty()
            if hasattr(self._stdout, "isatty")
            else False
        )
        is_ci = os.environ.get("CI", "").lower() in ("true", "1")
        return is_tty and not is_ci

    def _should_sync(self) -> bool:
        """Check if synchronized output should be used."""
        if not self._interactive:
            return False
        is_tty = (
            self._stdout.isatty()
            if hasattr(self._stdout, "isatty")
            else False
        )
        return is_tty

    def _can_write(self) -> bool:
        """Check if we can write to stdout."""
        if not hasattr(self._stdout, "closed"):
            return True
        return not self._stdout.closed

    def _get_window_size(self) -> tuple[int, int]:
        """Get the terminal window size."""
        try:
            size = shutil.get_terminal_size()
            return (size.columns, size.lines)
        except Exception:
            return (80, 24)

    def _setup_exit_handler(self) -> None:
        """Set up signal handlers for exit."""
        def signal_handler(signum, frame):
            self.unmount()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _setup_resize_handler(self) -> None:
        """Set up terminal resize handler."""
        def handle_sigwinch(signum, frame):
            current_width = self._get_window_size()[0]

            if current_width < self._last_terminal_width:
                self._log.clear()
                self._last_output = ""
                self._last_output_to_render = ""

            self._calculate_layout()
            self._on_render_callback()

            self._last_terminal_width = current_width

        signal.signal(signal.SIGWINCH, handle_sigwinch)

    def _setup_input_handler(self) -> None:
        """Set up keyboard input handler."""
        if not self._interactive:
            return

        import threading

        def read_input():
            try:
                while not self._is_unmounted:
                    if hasattr(self._stdin, "buffer"):
                        char = self._stdin.buffer.read(1)
                        if char:
                            try:
                                data = char.decode("utf-8")
                            except UnicodeDecodeError:
                                data = char.decode("latin-1")
                            _dispatch_input(data)
                    else:
                        data = self._stdin.read(1)
                        if data:
                            _dispatch_input(data)
            except Exception:
                pass

        # Start input thread
        thread = threading.Thread(target=read_input, daemon=True)
        thread.start()

    def _set_alternate_screen(self, enabled: bool) -> None:
        """Set alternate screen mode."""
        self._alternate_screen = (
            enabled
            and self._interactive
            and self._stdout.isatty() if hasattr(self._stdout, "isatty") else False
        )

        if self._alternate_screen:
            self._stdout.write(enter_alternative_screen())
            self._stdout.write(cursor_hide())
            self._stdout.flush()

    def _cleanup(self) -> None:
        """Clean up resources."""
        _set_rerender_callback(None)
        # Clear input handlers
        _clear_input_handlers()

        # Restore terminal state
        if self._can_write():
            if self._alternate_screen:
                self._stdout.write(exit_alternative_screen())
                self._stdout.write(cursor_show())
                self._alternate_screen = False

            if not self._interactive:
                self._stdout.write(
                    "\n" if self._debug else self._last_output + "\n"
                )
            elif not self._debug:
                self._log.done()

        self._stdout.flush()


def _throttle(func: Callable, wait: int) -> Callable:
    """
    Create a throttled version of a function.

    Args:
        func: Function to throttle.
        wait: Milliseconds to wait between calls.

    Returns:
        Throttled function.
    """
    last_call = [0.0]
    pending = [False]

    def throttled():
        now = time.time() * 1000
        remaining = wait - (now - last_call[0])

        if remaining <= 0:
            last_call[0] = now
            func()
            pending[0] = False
        elif not pending[0]:
            pending[0] = True
            import threading

            def later():
                time.sleep(remaining / 1000)
                last_call[0] = time.time() * 1000
                func()
                pending[0] = False

            threading.Thread(target=later, daemon=True).start()

    return throttled


def render_component(
    component: Union[VNode, Callable],
    *,
    stdout: Optional[TextIO] = None,
    stdin: Optional[TextIO] = None,
    stderr: Optional[TextIO] = None,
    **kwargs: Any,
) -> Ink:
    """
    Render a component.

    Args:
        component: The component to render.
        stdout: Standard output stream.
        stdin: Standard input stream.
        stderr: Standard error stream.
        **kwargs: Additional options.

    Returns:
        The Ink instance.
    """
    options = Options(
        stdout=stdout or sys.stdout,
        stdin=stdin or sys.stdin,
        stderr=stderr or sys.stderr,
        **kwargs,
    )

    app = Ink(options)
    app.render(component)

    return app


# Convenience function
def render(
    component: Union[VNode, Callable],
    **kwargs: Any,
) -> Ink:
    """
    Render a component.

    Args:
        component: The component to render.
        **kwargs: Additional options.

    Returns:
        The Ink instance.
    """
    return render_component(component, **kwargs)
