"""
Use Input example for ink-python.

Demonstrates keyboard input handling with arrow keys.
Port of js_source/ink/examples/use-input/use-input.tsx
"""

from ink_python import render, Box, Text, use_input, use_app


def robot_example():
    """A robot face that moves with arrow keys."""
    from ink_python.hooks import useState

    app = use_app()
    x, set_x = useState(1)
    y, set_y = useState(1)

    def handle_input(char, key):
        if char == "q":
            app.exit()
        if key.left_arrow:
            set_x(max(1, x - 1))
        if key.right_arrow:
            set_x(min(20, x + 1))
        if key.up_arrow:
            set_y(max(1, y - 1))
        if key.down_arrow:
            set_y(min(10, y + 1))

    use_input(handle_input)

    return Box(
        Text('Use arrow keys to move the face. Press "q" to exit.'),
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
