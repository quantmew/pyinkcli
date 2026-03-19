"""
Justify content example for pyinkcli.

Demonstrates different justifyContent values in flexbox layout.
"""

from pyinkcli import render, Box, Text, useApp, useInput


def justify_content_example():
    """Render boxes with different justifyContent values."""
    app = useApp()

    def on_input(input_char, key):
        if input_char == "q" or (key.ctrl and input_char == "c"):
            app.exit()

    useInput(on_input)

    return Box(
        Box(
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
        ),
        Text("\nPress 'q' to exit", dimColor=True),
        flexDirection="column",
    )


if __name__ == "__main__":
    render(justify_content_example).wait_until_exit()
