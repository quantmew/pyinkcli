"""
Terminal resize example for pyinkcli.

Demonstrates the useWindowSize hook to track terminal dimensions.
"""

from pyinkcli import render, Box, Text, useWindowSize


def terminal_resize_example():
    """Render terminal size information."""
    columns, rows = useWindowSize()

    return Box(
        Box(
            Text("Terminal Size", bold=True, color="cyan"),
            Text(f"Columns: {columns}"),
            Text(f"Rows: {rows}"),
            Box(
                Text(
                    "Resize your terminal to see the values update. Press Ctrl+C to exit.",
                    dimColor=True,
                ),
            ),
            flexDirection="column",
            padding=1,
        ),
    )


if __name__ == "__main__":
    render(terminal_resize_example).wait_until_exit()
