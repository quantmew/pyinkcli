"""Strict structure port of `js_source/ink/examples/router/router.tsx`."""

from pyinkcli import Box, Text, render, useApp, useInput
from pyinkcli.component import createElement
from pyinkcli.packages.react_router import MemoryRouter, Routes, Route, useNavigate


def Home():
    exit_ = useApp().exit
    navigate = useNavigate()

    def handle_input(input_char, key):
        if input_char == "q":
            exit_()

        if key.return_pressed:
            navigate("/about")

    useInput(handle_input)

    return Box(
        Text("Home", bold=True, color="green"),
        Text('Press Enter to go to About, or "q" to quit.'),
        flexDirection="column",
    )


def About():
    exit_ = useApp().exit
    navigate = useNavigate()

    def handle_input(input_char, key):
        if input_char == "q":
            exit_()

        if key.return_pressed:
            navigate("/")

    useInput(handle_input)

    return Box(
        Text("About", bold=True, color="blue"),
        Text('Press Enter to go back Home, or "q" to quit.'),
        flexDirection="column",
    )


def App():
    return createElement(
        MemoryRouter,
        createElement(
            Routes,
            createElement(Route, path="/", element=createElement(Home)),
            createElement(Route, path="/about", element=createElement(About)),
        ),
    )


if __name__ == "__main__":
    render(createElement(App)).wait_until_exit()
