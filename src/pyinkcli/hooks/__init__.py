"""Hooks for pyinkcli."""

from pyinkcli.hooks.use_app import useApp
from pyinkcli.hooks.use_input import useInput, Key
from pyinkcli.hooks.use_stdout import useStdout
from pyinkcli.hooks.use_stdin import useStdin
from pyinkcli.hooks.use_stderr import useStderr
from pyinkcli.hooks.use_window_size import useWindowSize
from pyinkcli.hooks.use_focus import useFocus
from pyinkcli.hooks._runtime import useState, useEffect, useRef, useMemo, useCallback
from pyinkcli.hooks.use_paste import usePaste
from pyinkcli.hooks.use_focus_manager import useFocusManager
from pyinkcli.hooks.use_is_screen_reader_enabled import useIsScreenReaderEnabled
from pyinkcli.hooks.use_cursor import useCursor
from pyinkcli.hooks.use_box_metrics import useBoxMetrics

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
