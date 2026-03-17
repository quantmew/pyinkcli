"""
Use focus example for ink-python.

Demonstrates the useFocus hook for keyboard navigation.
Press Tab to focus next element, Shift+Tab to focus previous, Esc to reset.
"""

from ink_python import render, Box, Text, use_focus


def focus_example():
    """Render focusable items."""
    return Box(
        Box(
            Text(
                "Press Tab to focus next element, Shift+Tab to focus previous element, "
                "Esc to reset focus."
            ),
            marginBottom=1,
        ),
        item_label("First", "first"),
        item_label("Second", "second"),
        item_label("Third", "third"),
        flexDirection="column",
        padding=1,
    )


def item_label(label: str, element_id: str):
    """Create a focusable item with label."""
    is_focused, _ = use_focus(id=element_id)
    status = Text("(focused)", color="green") if is_focused else Text("")
    return Text(f"{label} ", status)


if __name__ == "__main__":
    render(focus_example())
