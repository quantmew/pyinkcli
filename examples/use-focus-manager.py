"""
Use focus manager example for ink-python.

Demonstrates the useFocusManager hook for programmatic focus control.
"""

from ink_python import render, Box, Text, useFocusManager, useFocus, useInput, useApp
from ink_python.component import createElement


def focus_manager_example():
    """Render focusable items with programmatic focus control."""
    app = useApp()
    focus_mgr = useFocusManager()

    def on_input(input: str, key):
        if input == "q" or (key.ctrl and input == "c"):
            app.exit()
        elif key.tab:
            if key.shift:
                focus_mgr.focus_previous()
            else:
                focus_mgr.focus_next()
        elif key.escape:
            focus_mgr.disable_focus()

    useInput(on_input)

    return Box(
        Box(
            Text(
                "Press Tab to focus next, Shift+Tab for previous, Esc to disable focus, q to exit"
            ),
            marginBottom=1,
            dimColor=True,
        ),
        Box(
            Text(f"Active focus ID: {focus_mgr.active_id or 'None'}", color="yellow"),
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
    render(focus_manager_example).wait_until_exit()
