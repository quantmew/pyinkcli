"""Parity checks for the JS-like public surfaces."""

import ink_python
from ink_python import cursor_helpers
from ink_python import dom
from ink_python import index as ink_index
from ink_python import log_update
from ink_python import render_node_to_output
from ink_python import suspense_runtime
from ink_python import styles
from ink_python import yoga_compat
from ink_python import component
from ink_python.hooks import state as hooks_state
from ink_python.components import (
    AccessibilityContext,
    AppContext,
    BackgroundContext,
    CursorContext,
    FocusContext,
    StderrContext,
    StdinContext,
    StdoutContext,
)


def test_index_exports_match_js_surface() -> None:
    assert ink_index.__all__ == [
        "render",
        "renderToString",
        "Box",
        "Text",
        "Static",
        "Transform",
        "Newline",
        "Spacer",
        "Key",
        "useInput",
        "usePaste",
        "useApp",
        "useStdin",
        "useStdout",
        "useStderr",
        "useFocus",
        "useFocusManager",
        "useIsScreenReaderEnabled",
        "useCursor",
        "useWindowSize",
        "useBoxMetrics",
        "measureElement",
        "DOMElement",
        "kittyFlags",
        "kittyModifiers",
    ]


def test_root_package_all_matches_js_surface() -> None:
    assert ink_python.__all__ == ink_index.__all__


def test_root_package_no_longer_exposes_trimmed_compat_exports() -> None:
    for name in (
        "Ink",
        "TextNode",
        "createNode",
        "createTextNode",
        "Styles",
        "apply_styles",
        "Suspense",
        "createElement",
        "useState",
        "useEffect",
        "useRef",
        "useMemo",
        "useCallback",
        "useTransition",
    ):
        try:
            getattr(ink_python, name)
        except AttributeError:
            continue
        raise AssertionError(f"{name} should not be exposed from ink_python root package")


def test_cursor_helpers_export_camel_case_names() -> None:
    assert cursor_helpers.__all__ == [
        "CursorPosition",
        "CursorOnlyInput",
        "showCursorEscape",
        "hideCursorEscape",
        "cursorPositionChanged",
        "buildCursorSuffix",
        "buildReturnToBottom",
        "buildCursorOnlySequence",
        "buildReturnToBottomPrefix",
    ]


def test_render_node_to_output_exports_camel_case_names() -> None:
    assert render_node_to_output.__all__ == [
        "OutputTransformer",
        "applyPaddingToText",
        "indentString",
        "renderNodeToOutput",
        "renderNodeToScreenReaderOutput",
    ]


def test_dom_exports_match_js_like_public_names() -> None:
    assert dom.__all__ == [
        "DOMElement",
        "TextNode",
        "DOMNode",
        "DOMNodeAttribute",
        "ElementNames",
        "NodeNames",
        "createNode",
        "appendChildNode",
        "insertBeforeNode",
        "removeChildNode",
        "setAttribute",
        "setStyle",
        "createTextNode",
        "setTextNodeValue",
        "addLayoutListener",
        "emitLayoutListeners",
        "squashTextNodes",
    ]


def test_styles_exports_only_public_styles_type() -> None:
    assert styles.__all__ == ["Styles"]


def test_context_modules_export_js_like_primary_names() -> None:
    assert AccessibilityContext.__all__ == ["accessibilityContext"]
    assert AppContext.__all__ == ["AppContext", "Props"]
    assert BackgroundContext.__all__ == ["BackgroundColor", "backgroundContext"]
    assert CursorContext.__all__ == ["CursorContext"]
    assert FocusContext.__all__ == ["FocusContext"]
    assert StdinContext.__all__ == ["StdinContext"]
    assert StdoutContext.__all__ == ["StdoutContext"]
    assert StderrContext.__all__ == ["StderrContext"]


def test_log_update_exports_only_primary_public_names() -> None:
    assert log_update.__all__ == ["LogUpdate", "logUpdate"]


def test_suspense_runtime_module_is_now_thin_compat_surface() -> None:
    assert suspense_runtime.__all__ == [
        "SuspendSignal",
        "readResource",
        "preloadResource",
        "peekResource",
        "invalidateResource",
        "resetResource",
        "resetAllResources",
    ]


def test_yoga_compat_remains_compat_facade() -> None:
    assert yoga_compat.__all__ == [
        "LayoutNode",
        "Node",
        "Config",
        "YGDirection",
        "DIRECTION_INHERIT",
        "DIRECTION_LTR",
        "DIRECTION_RTL",
        "YGFlexDirection",
        "FLEX_DIRECTION_COLUMN",
        "FLEX_DIRECTION_COLUMN_REVERSE",
        "FLEX_DIRECTION_ROW",
        "FLEX_DIRECTION_ROW_REVERSE",
        "YGJustify",
        "JUSTIFY_FLEX_START",
        "JUSTIFY_CENTER",
        "JUSTIFY_FLEX_END",
        "JUSTIFY_SPACE_BETWEEN",
        "JUSTIFY_SPACE_AROUND",
        "JUSTIFY_SPACE_EVENLY",
        "YGAlign",
        "ALIGN_AUTO",
        "ALIGN_FLEX_START",
        "ALIGN_CENTER",
        "ALIGN_FLEX_END",
        "ALIGN_STRETCH",
        "ALIGN_BASELINE",
        "ALIGN_SPACE_BETWEEN",
        "ALIGN_SPACE_AROUND",
        "ALIGN_SPACE_EVENLY",
        "YGWrap",
        "WRAP_NO_WRAP",
        "WRAP_WRAP",
        "WRAP_WRAP_REVERSE",
        "YGPositionType",
        "POSITION_TYPE_STATIC",
        "POSITION_TYPE_RELATIVE",
        "POSITION_TYPE_ABSOLUTE",
        "YGDisplay",
        "DISPLAY_FLEX",
        "DISPLAY_NONE",
        "YGEdge",
        "EDGE_LEFT",
        "EDGE_TOP",
        "EDGE_RIGHT",
        "EDGE_BOTTOM",
        "EDGE_START",
        "EDGE_END",
        "EDGE_HORIZONTAL",
        "EDGE_VERTICAL",
        "EDGE_ALL",
        "YGGutter",
        "GUTTER_COLUMN",
        "GUTTER_ROW",
        "GUTTER_ALL",
        "UNDEFINED",
    ]
    assert yoga_compat.Node is not None
    assert yoga_compat.EDGE_LEFT is not None


def test_component_module_is_now_thin_compat_surface() -> None:
    assert component.__all__ == ["createElement", "component", "isElement", "RenderableNode"]


def test_hooks_state_module_is_now_thin_compat_surface() -> None:
    assert hooks_state.__all__ == [
        "useState",
        "useEffect",
        "useRef",
        "useMemo",
        "useCallback",
        "useReducer",
        "Ref",
    ]
