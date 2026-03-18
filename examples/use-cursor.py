"""
Use cursor example for ink-python.

Demonstrates the useCursor hook to control cursor visibility.
"""

from ink_python import render, Box, Text, useCursor, useInput, useApp


def cursor_example():
    """Render content with hidden cursor."""
    app = useApp()

    # Hide cursor
    useCursor(False)

    # Exit on 'q'
    def on_input(input: str, key):
        if input == "q" or (key.ctrl and input == "c"):
            app.exit()

    useInput(on_input)

    return Box(
        Text("Cursor is hidden!", bold=True, color="green"),
        Text("\nPress 'q' to exit", dimColor=True),
        flexDirection="column",
        padding=1,
    )


if __name__ == "__main__":
    render(cursor_example).wait_until_exit()
