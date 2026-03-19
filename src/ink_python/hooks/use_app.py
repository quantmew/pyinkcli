"""
useApp hook for ink-python.

Provides access to the Ink app instance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ink_python.components._app_context_runtime import _get_app_context
from ink_python.hooks._runtime import _queue_after_current_batch

if TYPE_CHECKING:
    from ink_python.ink import Ink


class _AppHandle:
    """Handle to the Ink application instance."""

    def __init__(self, ink_instance: Optional["Ink"] = None):
        self._ink = ink_instance
        self._exit_handlers: list[callable] = []

    def exit(self, error_or_result: Optional[Any] = None) -> None:
        """
        Exit the application.

        Args:
            error_or_result: Optional exit error or result.
        """
        if self._ink is not None:
            _queue_after_current_batch(
                lambda: self._ink._handle_app_exit(error_or_result)
            )

    def wait_until_exit(self) -> Any:
        """Wait for the application to exit."""
        if self._ink is not None:
            return self._ink.wait_until_exit()
        return None

    def wait_until_render_flush(self, timeout: Optional[float] = None) -> Any:
        """Wait for pending render output to flush."""
        if self._ink is not None:
            return self._ink.wait_until_render_flush(timeout=timeout)
        return None

    def clear(self) -> None:
        """Clear the terminal output."""
        if self._ink is not None:
            self._ink.clear()

    def on_exit(self, handler: callable) -> callable:
        """
        Register an exit handler.

        Args:
            handler: Function to call on exit.

        Returns:
            Unsubscribe function.
        """
        self._exit_handlers.append(handler)
        return lambda: self._exit_handlers.remove(handler)

    def _set_ink(self, ink_instance: "Ink") -> None:
        """Set the Ink instance."""
        self._ink = ink_instance


# Global app handle
_app_handle: Optional[_AppHandle] = None


def useApp() -> _AppHandle:
    """
    Hook to access the Ink application instance.

    Returns:
        AppHandle with methods to control the app.
    """
    app_context = _get_app_context()
    if app_context is not None and getattr(app_context, "app", None) is not None:
        return _AppHandle(app_context.app)

    global _app_handle
    if _app_handle is None:
        _app_handle = _AppHandle()
    return _app_handle


def _set_app_ink(ink_instance: "Ink") -> None:
    """Internal: Set the Ink instance on the global app handle."""
    global _app_handle
    if _app_handle is None:
        _app_handle = _AppHandle(ink_instance)
    else:
        _app_handle._set_ink(ink_instance)
