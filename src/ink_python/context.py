"""
Context API for ink-python.

Provides context management similar to React's Context API.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Callable, Generator, Generic, Optional, TypeVar

T = TypeVar("T")


class Context(Generic[T]):
    """
    A context object for sharing data across the component tree.

    Similar to React's Context API.
    """

    def __init__(self, default_value: Optional[T] = None, name: str = ""):
        self._default_value = default_value
        self._name = name
        self._var: ContextVar[Optional[T]] = ContextVar(
            f"ink_context_{name}_{id(self)}", default=default_value
        )

    @property
    def default_value(self) -> Optional[T]:
        """Get the default value."""
        return self._default_value

    def get(self) -> Optional[T]:
        """Get the current context value."""
        return self._var.get()

    def set(self, value: Optional[T]) -> None:
        """Set the context value."""
        self._var.set(value)

    @contextmanager
    def provider(self, value: T) -> Generator[None, None, None]:
        """Context manager for providing a value."""
        token = self._var.set(value)
        try:
            yield
        finally:
            self._var.reset(token)


def create_context(default_value: Optional[T] = None, name: str = "") -> Context[T]:
    """
    Create a new context.

    Args:
        default_value: The default value for the context.
        name: Optional name for debugging.

    Returns:
        A new Context instance.
    """
    return Context(default_value=default_value, name=name)


def use_context(context: Context[T]) -> Optional[T]:
    """
    Get the current value from a context.

    Args:
        context: The context to read from.

    Returns:
        The current context value.
    """
    return context.get()


# Built-in contexts
class AppContext:
    """Context for the app instance."""

    def __init__(self, app: Any):
        self.app = app
        self.stdin: Any = None
        self.stdout: Any = None
        self.stderr: Any = None
        self.exit_on_ctrl_c: bool = True
        self.interactive: bool = True
        self.write_to_stdout: Optional[Callable[[str], None]] = None
        self.write_to_stderr: Optional[Callable[[str], None]] = None
        self.set_cursor_position: Optional[Callable[[tuple[int, int]], None]] = None
        self.on_exit: Optional[Callable[[Any], None]] = None
        self.on_wait_until_render_flush: Optional[Callable[[], None]] = None


# Global context instances
_app_context: ContextVar[Optional[AppContext]] = ContextVar("app_context", default=None)
_stdin_context: ContextVar[Any] = ContextVar("stdin_context", default=None)
_stdout_context: ContextVar[Any] = ContextVar("stdout_context", default=None)
_stderr_context: ContextVar[Any] = ContextVar("stderr_context", default=None)
_accessibility_context: ContextVar[dict[str, bool]] = ContextVar(
    "accessibility_context", default={"isScreenReaderEnabled": False}
)
_background_context: ContextVar[Optional[str]] = ContextVar(
    "background_context", default=None
)


def get_app_context() -> Optional[AppContext]:
    """Get the current app context."""
    return _app_context.get()


def set_app_context(app: AppContext) -> None:
    """Set the app context."""
    _app_context.set(app)


def get_stdin() -> Any:
    """Get the current stdin stream."""
    return _stdin_context.get()


def get_stdout() -> Any:
    """Get the current stdout stream."""
    return _stdout_context.get()


def get_stderr() -> Any:
    """Get the current stderr stream."""
    return _stderr_context.get()


def is_screen_reader_enabled() -> bool:
    """Check if screen reader mode is enabled."""
    return _accessibility_context.get().get("isScreenReaderEnabled", False)


def get_background_color() -> Optional[str]:
    """Get the inherited background color."""
    return _background_context.get()


@contextmanager
def provide_app_context(app: AppContext) -> Generator[None, None, None]:
    """Provide an app context."""
    token = _app_context.set(app)
    try:
        yield
    finally:
        _app_context.reset(token)


@contextmanager
def provide_stdin(stdin: Any) -> Generator[None, None, None]:
    """Provide a stdin stream."""
    token = _stdin_context.set(stdin)
    try:
        yield
    finally:
        _stdin_context.reset(token)


@contextmanager
def provide_stdout(stdout: Any) -> Generator[None, None, None]:
    """Provide a stdout stream."""
    token = _stdout_context.set(stdout)
    try:
        yield
    finally:
        _stdout_context.reset(token)


@contextmanager
def provide_stderr(stderr: Any) -> Generator[None, None, None]:
    """Provide a stderr stream."""
    token = _stderr_context.set(stderr)
    try:
        yield
    finally:
        _stderr_context.reset(token)


@contextmanager
def provide_accessibility(enabled: bool) -> Generator[None, None, None]:
    """Provide accessibility context."""
    token = _accessibility_context.set({"isScreenReaderEnabled": enabled})
    try:
        yield
    finally:
        _accessibility_context.reset(token)


@contextmanager
def provide_background_color(color: Optional[str]) -> Generator[None, None, None]:
    """Provide background color context."""
    token = _background_context.set(color)
    try:
        yield
    finally:
        _background_context.reset(token)
