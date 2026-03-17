"""
Justify content example for ink-python.

Demonstrates different justifyContent values in flexbox layout.
"""

from ink_python import render, Box, Text, use_app, use_input


def justify_content_example():
    """Render boxes with different justifyContent values."""
    app = use_app()

    def on_input(input_char, key):
        if input_char == 'q' or (key.get('ctrl') and input_char == 'c'):
            app.exit()

    use_input(on_input)

    return Box(
        Box(
            Text("["),
            Box(
                Text("X"),
                Text("Y"),
                justifyContent="flex-start",
                width=20,
                height=1,
            ),
            Text("] flex-start"),
        ),
        Box(
            Text("["),
            Box(
                Text("X"),
                Text("Y"),
                justifyContent="flex-end",
                width=20,
                height=1,
            ),
            Text("] flex-end"),
        ),
        Box(
            Text("["),
            Box(
                Text("X"),
                Text("Y"),
                justifyContent="center",
                width=20,
                height=1,
            ),
            Text("] center"),
        ),
        Box(
            Text("["),
            Box(
                Text("X"),
                Text("Y"),
                justifyContent="space-around",
                width=20,
                height=1,
            ),
            Text("] space-around"),
        ),
        Box(
            Text("["),
            Box(
                Text("X"),
                Text("Y"),
                justifyContent="space-between",
                width=20,
                height=1,
            ),
            Text("] space-between"),
        ),
        Box(
            Text("["),
            Box(
                Text("X"),
                Text("Y"),
                justifyContent="space-evenly",
                width=20,
                height=1,
            ),
            Text("] space-evenly"),
        ),
        flexDirection="column",
    ), Text("\nPress 'q' to exit", dimColor=True)


if __name__ == "__main__":
    render(justify_content_example())
