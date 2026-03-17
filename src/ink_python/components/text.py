"""
Text component for ink-python.

Displays styled text in the terminal.
"""

from __future__ import annotations

from typing import Any, Optional, Union

from ink_python.component import VNode, create_vnode, component
from ink_python.context import get_background_color, is_screen_reader_enabled
from ink_python.styles import Styles
from ink_python.colorize import colorize


@component
def Text(
    *children: Union[VNode, str, None],
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
) -> Optional[VNode]:
    """
    Text component - displays styled text.

    Args:
        *children: Text content.
        color: Foreground color.
        background_color: Background color.
        dim_color: Dim the text.
        bold: Make text bold.
        italic: Make text italic.
        underline: Make text underlined.
        strikethrough: Make text crossed out.
        inverse: Invert colors.
        wrap: Text wrapping mode.
        aria_label: Accessibility label.
        aria_hidden: Hide from screen readers.
        **kwargs: Additional props.

    Returns:
        A VNode representing the text.
    """
    # Check screen reader mode
    if is_screen_reader_enabled() and aria_hidden:
        return None

    # Get inherited background color
    inherited_bg = get_background_color()

    # Determine content
    content: list[Union[VNode, str, None]] = []
    if is_screen_reader_enabled() and aria_label:
        content.append(aria_label)
    else:
        content.extend(children)

    # If no content, return None
    if not content:
        return None

    # If all children are strings, combine them
    if all(isinstance(c, str) for c in content):
        text_content = "".join(content)
        if not text_content:
            return None

        # Create transform function for styling
        def transform(s: str, index: int) -> str:
            result = s

            if dim_color:
                result = _dim(result)
            if color:
                result = colorize(result, color, "foreground")
            if background_color:
                result = colorize(result, background_color, "background")
            elif inherited_bg:
                result = colorize(result, inherited_bg, "background")
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

        return create_vnode(
            "ink-text",
            text_content,
            style={
                "flexGrow": 0,
                "flexShrink": 1,
                "flexDirection": "row",
                "textWrap": wrap,
            },
            internal_transform=transform,
        )

    # Complex children - create text wrapper
    return create_vnode(
        "ink-text",
        *content,
        style={
            "flexGrow": 0,
            "flexShrink": 1,
            "flexDirection": "row",
            "textWrap": wrap,
        },
    )


def text(
    *children: Union[VNode, str, None],
    **kwargs: Any,
) -> Optional[VNode]:
    """
    Lowercase alias for Text component.

    Args:
        *children: Text content.
        **kwargs: Text properties.

    Returns:
        A VNode representing the text.
    """
    return Text(*children, **kwargs)


# Style helper functions using ANSI codes
def _dim(text: str) -> str:
    """Apply dim styling."""
    return f"\x1b[2m{text}\x1b[22m"


def _bold(text: str) -> str:
    """Apply bold styling."""
    return f"\x1b[1m{text}\x1b[22m"


def _italic(text: str) -> str:
    """Apply italic styling."""
    return f"\x1b[3m{text}\x1b[23m"


def _underline(text: str) -> str:
    """Apply underline styling."""
    return f"\x1b[4m{text}\x1b[24m"


def _strikethrough(text: str) -> str:
    """Apply strikethrough styling."""
    return f"\x1b[9m{text}\x1b[29m"


def _inverse(text: str) -> str:
    """Apply inverse styling."""
    return f"\x1b[7m{text}\x1b[27m"
