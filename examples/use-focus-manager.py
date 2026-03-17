"""
Use focus manager example for ink-python.

Demonstrates the useFocusManager hook for programmatic focus control.
"""

from ink_python import render, Box, Text, use_focus_manager, use_focus, use_input, use_app


def focus_manager_example():
    """Render focusable items with programmatic focus control."""
    app = use_app()
    focus_mgr = use_focus_manager()

    def on_input(input: str, key: dict):
        if input == "q" or (key.get("ctrl", False) and input == "c"):
            app.exit()
        elif input == "\t":  # Tab
            if key.get("shift", False):
                focus_mgr.focus_previous()
            else:
                focus_mgr.focus_next()
        elif input == "\x1b":  # Esc
            focus_mgr.disable_focus()

    use_input(on_input)

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
    render(focus_manager_example())
