"""Hooks for ink-python."""

from ink_python.hooks.use_app import useApp, use_app
from ink_python.hooks.use_input import useInput, use_input, Key
from ink_python.hooks.use_stdout import useStdout, use_stdout
from ink_python.hooks.use_stdin import useStdin, use_stdin
from ink_python.hooks.use_stderr import useStderr, use_stderr
from ink_python.hooks.use_window_size import useWindowSize, use_window_size
from ink_python.hooks.use_focus import useFocus, use_focus
from ink_python.hooks.state import useState, useEffect, useRef, useMemo, useCallback
from ink_python.hooks.use_paste import usePaste, use_paste
from ink_python.hooks.use_focus_manager import useFocusManager, use_focus_manager
from ink_python.hooks.use_is_screen_reader_enabled import useIsScreenReaderEnabled, use_is_screen_reader_enabled
from ink_python.hooks.use_cursor import useCursor, use_cursor
from ink_python.hooks.use_box_metrics import useBoxMetrics, use_box_metrics, BoxMetrics, UseBoxMetricsResult

__all__ = [
    "useApp",
    "use_app",
    "useInput",
    "use_input",
    "Key",
    "useStdout",
    "use_stdout",
    "useStdin",
    "use_stdin",
    "useStderr",
    "use_stderr",
    "useWindowSize",
    "use_window_size",
    "useFocus",
    "use_focus",
    "useState",
    "useEffect",
    "useRef",
    "useMemo",
    "useCallback",
    # New hooks
    "usePaste",
    "use_paste",
    "useFocusManager",
    "use_focus_manager",
    "useIsScreenReaderEnabled",
    "use_is_screen_reader_enabled",
    "useCursor",
    "use_cursor",
    "useBoxMetrics",
    "use_box_metrics",
    "BoxMetrics",
    "UseBoxMetricsResult",
]
