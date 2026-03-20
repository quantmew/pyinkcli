"""
Text component for pyinkcli.

Canonical component module matching JS basename.
"""

from __future__ import annotations

from typing import Any

from pyinkcli._component_runtime import RenderableNode, component, createElement
from pyinkcli.colorize import colorize
from pyinkcli.components._accessibility_runtime import _is_screen_reader_enabled
from pyinkcli.components._background_runtime import _get_background_color

_UNSET = object()


@component
def Text(
    *children: RenderableNode,
    color: str | None = None,
    background_color: str | None = None,
    dim_color: bool = False,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    strikethrough: bool = False,
    inverse: bool = False,
    wrap: str = "wrap",
    aria_label: str | None = None,
    aria_hidden: bool = False,
    **kwargs: Any,
) -> RenderableNode:
    if "backgroundColor" in kwargs and background_color is None:
        background_color = kwargs.pop("backgroundColor")
    if "dimColor" in kwargs:
        dim_color = bool(kwargs.pop("dimColor"))
    if "ariaLabel" in kwargs and aria_label is None:
        aria_label = kwargs.pop("ariaLabel")
    if "ariaHidden" in kwargs:
        aria_hidden = bool(kwargs.pop("ariaHidden"))

    is_screen_reader_enabled = _is_screen_reader_enabled()
    if is_screen_reader_enabled and aria_hidden:
        return None

    inherited_background = _get_background_color()
    explicit_background = background_color if background_color is not None else _UNSET
    effective_background = (
        inherited_background if explicit_background is _UNSET else explicit_background
    )

    children_or_aria_label: list[RenderableNode] = []
    if is_screen_reader_enabled and aria_label:
        children_or_aria_label.append(aria_label)
    else:
        children_or_aria_label.extend(children)

    if not children_or_aria_label:
        return None

    def transform(text: str, index: int) -> str:
        result = text
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
        *children_or_aria_label,
        style={
            "flexGrow": 0,
            "flexShrink": 1,
            "flexDirection": "row",
            "textWrap": wrap,
        },
        internal_transform=transform,
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
