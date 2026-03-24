from ._runtime import (
    useCallback,
    useEffect,
    useInsertionEffect,
    useLayoutEffect,
    useMemo,
    useReducer,
    useRef,
    useState,
    useTransition,
)

__all__ = [
    "useApp",
    "useCallback",
    "useCursor",
    "useEffect",
    "useFocus",
    "useFocusManager",
    "useInput",
    "useInsertionEffect",
    "useIsScreenReaderEnabled",
    "useLayoutEffect",
    "useMemo",
    "usePaste",
    "useReducer",
    "useRef",
    "useState",
    "useStderr",
    "useStdin",
    "useStdout",
    "useTransition",
    "useWindowSize",
    "useBoxMetrics",
]


def __getattr__(name):
    if name == "useApp":
        from .use_app import useApp

        return useApp
    if name == "useBoxMetrics":
        from .use_box_metrics import useBoxMetrics

        return useBoxMetrics
    if name == "useCursor":
        from .use_cursor import useCursor

        return useCursor
    if name == "useFocus":
        from .use_focus import useFocus

        return useFocus
    if name == "useFocusManager":
        from .use_focus_manager import useFocusManager

        return useFocusManager
    if name == "useInput":
        from .use_input import useInput

        return useInput
    if name == "useIsScreenReaderEnabled":
        from .use_is_screen_reader_enabled import useIsScreenReaderEnabled

        return useIsScreenReaderEnabled
    if name == "usePaste":
        from .use_paste import usePaste

        return usePaste
    if name == "useStderr":
        from .use_stderr import useStderr

        return useStderr
    if name == "useStdin":
        from .use_stdin import useStdin

        return useStdin
    if name == "useStdout":
        from .use_stdout import useStdout

        return useStdout
    if name == "useWindowSize":
        from .use_window_size import useWindowSize

        return useWindowSize
    raise AttributeError(name)
