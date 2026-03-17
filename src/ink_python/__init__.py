"""
ink-python - React-like terminal UI library for Python

A port of the JavaScript Ink library for building interactive CLI apps.
"""

from ink_python.ink import Ink, render, render_component
from ink_python.render_to_string import render_to_string, renderToString
from ink_python.measure_element import measure_element, measureElement
from ink_python.component import (
    VNode,
    create_vnode,
    component,
    h,
    Fragment,
    fragment,
)
from ink_python.components import Box, Text, Newline, Spacer, Static, Transform
from ink_python.dom import DOMElement, TextNode, create_node, create_text_node
from ink_python.styles import Styles, apply_styles
from ink_python.hooks import (
    useApp,
    use_app,
    useInput,
    use_input,
    Key,
    useStdout,
    use_stdout,
    useStdin,
    use_stdin,
    useStderr,
    use_stderr,
    useWindowSize,
    use_window_size,
    useFocus,
    use_focus,
    useState,
    useEffect,
    useRef,
    useMemo,
    useCallback,
    usePaste,
    use_paste,
    useFocusManager,
    use_focus_manager,
    useIsScreenReaderEnabled,
    use_is_screen_reader_enabled,
    useCursor,
    use_cursor,
    useBoxMetrics,
    use_box_metrics,
    BoxMetrics,
    UseBoxMetricsResult,
)

__version__ = "0.1.0"
__all__ = [
    # Main exports
    "render",
    "render_component",
    "render_to_string",
    "renderToString",
    "measure_element",
    "measureElement",
    "Ink",
    # Components
    "Box",
    "Text",
    "Newline",
    "Spacer",
    "Static",
    "Transform",
    # VNode
    "VNode",
    "create_vnode",
    "component",
    "h",
    "Fragment",
    "fragment",
    # DOM
    "DOMElement",
    "TextNode",
    "create_node",
    "create_text_node",
    # Styles
    "Styles",
    "apply_styles",
    # Hooks
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
