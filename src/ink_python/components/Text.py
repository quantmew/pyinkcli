"""
Text component for ink-python.

Canonical component module matching JS basename.
"""

from __future__ import annotations

from typing import Any, Optional

from ink_python.colorize import colorize
from ink_python._component_runtime import RenderableNode, component, createElement
from ink_python.components._accessibility_runtime import _is_screen_reader_enabled
from ink_python.components._background_runtime import _get_background_color


@component
def Text(
    *children: RenderableNode,
    color: Optional[str] = None,
    background_color: Optional[str] = None,
    dim_color: bool = False,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    strikethrough: bool = False,
    inverse: bool = False,
    wrap: str = "wrap",
    aria_label: Optional[str] = None,
    aria_hidden: bool = False,
    **kwargs: Any,
) -> RenderableNode:
    if _is_screen_reader_enabled() and aria_hidden:
        return None

    inherited_background = _get_background_color()
    effective_background = (
        background_color if background_color is not None else inherited_background
    )

    content: list[RenderableNode] = []
    if _is_screen_reader_enabled() and aria_label:
        content.append(aria_label)
    else:
        content.extend(children)

    if not content:
        return None

    if all(isinstance(c, str) for c in content):
        text_content = "".join(content)
        if not text_content:
            return None

        def transform(s: str, index: int) -> str:
            result = s
            if dim_color:
                result = _dim(result)
            if color:
                result = colorize(result, color, "foreground")
            if effective_background:
                result = colorize(result, effective_background, "background")
            if bold:
                result = _bold(result)
            if italic:
                result = _italic(result)
            if underline:
                result = _underline(result)
            if strikethrough:
                result = _strikethrough(result)
            if inverse:
                result = _inverse(result)
            return result

        return createElement(
            "ink-text",
            text_content,
            style={
                "flexGrow": 0,
                "flexShrink": 1,
                "flexDirection": "row",
                "textWrap": wrap,
                "backgroundColor": effective_background,
            },
            internal_transform=transform,
        )

    return createElement(
        "ink-text",
        *content,
        style={
            "flexGrow": 0,
            "flexShrink": 1,
            "flexDirection": "row",
            "textWrap": wrap,
            "backgroundColor": effective_background,
        },
    )


def _dim(text: str) -> str:
    return f"\x1b[2m{text}\x1b[22m"


def _bold(text: str) -> str:
    return f"\x1b[1m{text}\x1b[22m"


def _italic(text: str) -> str:
    return f"\x1b[3m{text}\x1b[23m"


def _underline(text: str) -> str:
    return f"\x1b[4m{text}\x1b[24m"


def _strikethrough(text: str) -> str:
    return f"\x1b[9m{text}\x1b[29m"


def _inverse(text: str) -> str:
    return f"\x1b[7m{text}\x1b[27m"


__all__ = ["Text"]
