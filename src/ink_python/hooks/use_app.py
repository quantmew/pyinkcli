"""
useApp hook for ink-python.

Provides access to the Ink app instance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ink_python.ink import Ink


class AppHandle:
    """Handle to the Ink application instance."""

    def __init__(self, ink_instance: Optional["Ink"] = None):
        self._ink = ink_instance
        self._exit_handlers: list[callable] = []

    def exit(self, error: Optional[Exception] = None) -> None:
        """
        Exit the application.

        Args:
            error: Optional error to pass to exit handler.
        """
        if self._ink is not None:
            self._ink.unmount(error)

    def wait_until_exit(self) -> Any:
        """Wait for the application to exit."""
        if self._ink is not None:
            return self._ink.wait_until_exit()
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
_app_handle: Optional[AppHandle] = None


def useApp() -> AppHandle:
    """
    Hook to access the Ink application instance.

    Returns:
        AppHandle with methods to control the app.
    """
    global _app_handle
    if _app_handle is None:
        _app_handle = AppHandle()
    return _app_handle


def use_app() -> AppHandle:
    """Alias for useApp."""
    return useApp()


def _set_app_ink(ink_instance: "Ink") -> None:
    """Internal: Set the Ink instance on the global app handle."""
    global _app_handle
    if _app_handle is None:
        _app_handle = AppHandle(ink_instance)
    else:
        _app_handle._set_ink(ink_instance)
