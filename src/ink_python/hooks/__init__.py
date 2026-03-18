"""Hooks for ink-python."""

from ink_python.hooks.use_app import useApp
from ink_python.hooks.use_input import useInput, Key
from ink_python.hooks.use_stdout import useStdout
from ink_python.hooks.use_stdin import useStdin
from ink_python.hooks.use_stderr import useStderr
from ink_python.hooks.use_window_size import useWindowSize
from ink_python.hooks.use_focus import useFocus
from ink_python.hooks._runtime import useState, useEffect, useRef, useMemo, useCallback
from ink_python.hooks.use_paste import usePaste
from ink_python.hooks.use_focus_manager import useFocusManager
from ink_python.hooks.use_is_screen_reader_enabled import useIsScreenReaderEnabled
from ink_python.hooks.use_cursor import useCursor
from ink_python.hooks.use_box_metrics import useBoxMetrics

__all__ = [
    "useApp",
    "useInput",
    "Key",
    "useStdout",
    "useStdin",
    "useStderr",
    "useWindowSize",
    "useFocus",
    "useState",
    "useEffect",
    "useRef",
    "useMemo",
    "useCallback",
    # New hooks
    "usePaste",
    "useFocusManager",
    "useIsScreenReaderEnabled",
    "useCursor",
    "useBoxMetrics",
]
