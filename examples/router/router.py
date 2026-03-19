"""
Router example for pyinkcli.

Simple in-memory route switching inspired by js_source/ink/examples/router/router.tsx
"""

from pyinkcli import render, Box, Text, useInput, useApp
from pyinkcli.component import createElement


def Home(*, set_route):
    app = useApp()

    def handle_input(char, key):
        if char == "q":
            app.exit()
        if key.return_pressed:
            set_route("/about")

    useInput(handle_input)

    return Box(
        Text("Home", bold=True, color="green"),
        Text('Press Enter to go to About, or "q" to quit.'),
        flexDirection="column",
    )


def About(*, set_route):
    app = useApp()

    def handle_input(char, key):
        if char == "q":
            app.exit()
        if key.return_pressed:
            set_route("/")

    useInput(handle_input)

    return Box(
        Text("About", bold=True, color="blue"),
        Text('Press Enter to go back Home, or "q" to quit.'),
        flexDirection="column",
    )


def router_example():
    """Render a tiny two-page router demo."""
    from pyinkcli.hooks import useState

    route, set_route = useState("/")

    if route == "/":
        return createElement(Home, set_route=set_route)

    return createElement(About, set_route=set_route)


if __name__ == "__main__":
    render(router_example).wait_until_exit()
