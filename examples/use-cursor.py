"""
Use cursor example for ink-python.

Demonstrates the useCursor hook to control cursor visibility.
"""

from ink_python import render, Box, Text, use_cursor, use_input, use_app


def cursor_example():
    """Render content with hidden cursor."""
    app = use_app()

    # Hide cursor
    use_cursor(False)

    # Exit on 'q'
    def on_input(input: str, key: dict):
        if input == "q" or key.get("ctrl", False) and input == "c":
            app.exit()

    use_input(on_input)

    return Box(
        Text("Cursor is hidden!", bold=True, color="green"),
        Text("\nPress 'q' to exit", dimColor=True),
        flexDirection="column",
        padding=1,
    )


if __name__ == "__main__":
    render(cursor_example())
