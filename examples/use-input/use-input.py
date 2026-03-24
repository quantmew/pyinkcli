"""
Use Input example for pyinkcli.

Demonstrates keyboard input handling with arrow keys.
Port of js_source/ink/examples/use-input/use-input.tsx
"""

from pyinkcli import Box, Text, render, useApp, useInput


def robot_example():
    """A robot face that moves with arrow keys."""
    from pyinkcli.hooks import useState

    app = useApp()
    x, set_x = useState(1)
    y, set_y = useState(1)

    def handle_input(char, key):
        if char == "q":
            app.exit()
        if key.left_arrow:
            set_x(lambda current_x: max(1, current_x - 1))
        if key.right_arrow:
            set_x(lambda current_x: min(20, current_x + 1))
        if key.up_arrow:
            set_y(lambda current_y: max(1, current_y - 1))
        if key.down_arrow:
            set_y(lambda current_y: min(10, current_y + 1))

    useInput(handle_input)

    return Box(
        Text("Use arrow keys to move the face. Press “q” to exit."),
        Box(
            Text("^_^"),
            height=12,
            paddingLeft=x,
            paddingTop=y,
        ),
        flexDirection="column",
    )


if __name__ == "__main__":
    render(robot_example).wait_until_exit()
