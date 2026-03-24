"""
Use focus example for pyinkcli.

Demonstrates the useFocus hook for keyboard navigation.
Press Tab to focus next element, Shift+Tab to focus previous, Esc to reset.
"""

from pyinkcli import Box, Text, render, useFocus
from pyinkcli.component import createElement


def focus_example():
    """Render focusable items."""
    return Box(
        Box(
            Text(
                "Press Tab to focus next element, Shift+Tab to focus previous element, Esc to\n"
                "reset focus."
            ),
            marginBottom=1,
        ),
        createElement(ItemLabel, label="First", element_id="first"),
        createElement(ItemLabel, label="Second", element_id="second"),
        createElement(ItemLabel, label="Third", element_id="third"),
        flexDirection="column",
        padding=1,
    )


def ItemLabel(*, label: str, element_id: str):
    """Create a focusable item with label."""
    is_focused, _ = useFocus(id=element_id)
    return Box(
        Text(label),
        Text(" (focused)", color="green") if is_focused else Text(""),
    )


if __name__ == "__main__":
    render(focus_example).wait_until_exit()
