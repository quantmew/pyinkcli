"""
Borders example for ink-python.

Demonstrates different border styles available in ink-python.
"""

from ink_python import render, Box, Text, use_app, use_input


def borders_example():
    """Render boxes with different border styles."""
    app = use_app()

    def on_input(input_char, key):
        if input_char == 'q' or (key.get('ctrl') and input_char == 'c'):
            app.exit()

    use_input(on_input)

    return Box(
        Box(
            Box(
                Text("single"),
                borderStyle="single",
                marginRight=2,
            ),
            Box(
                Text("double"),
                borderStyle="double",
                marginRight=2,
            ),
            Box(
                Text("round"),
                borderStyle="round",
                marginRight=2,
            ),
            Box(
                Text("bold"),
                borderStyle="bold",
            ),
        ),
        Box(
            Box(
                Text("singleDouble"),
                borderStyle="singleDouble",
                marginRight=2,
            ),
            Box(
                Text("doubleSingle"),
                borderStyle="doubleSingle",
                marginRight=2,
            ),
            Box(
                Text("classic"),
                borderStyle="classic",
            ),
            marginTop=1,
        ),
        flexDirection="column",
        padding=2,
    ), Text("\nPress 'q' to exit", dimColor=True)


if __name__ == "__main__":
    render(borders_example())
