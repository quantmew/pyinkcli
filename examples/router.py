"""
Router example for ink-python.

Simple in-memory route switching inspired by js_source/ink/examples/router/router.tsx
"""

from ink_python import render, Box, Text, use_input, use_app


def router_example():
    """Render a tiny two-page router demo."""
    from ink_python.hooks import useState

    app = use_app()
    route, set_route = useState("/")

    def handle_input(char, key):
        if char == "q":
            app.exit()
        if key.return_pressed:
            set_route("/about" if route == "/" else "/")

    use_input(handle_input)

    if route == "/":
        return Box(
            Text("Home", bold=True, color="green"),
            Text('Press Enter to go to About, or "q" to quit.'),
            flexDirection="column",
        )

    return Box(
        Text("About", bold=True, color="blue"),
        Text('Press Enter to go back Home, or "q" to quit.'),
        flexDirection="column",
    )


if __name__ == "__main__":
    render(router_example).wait_until_exit()
