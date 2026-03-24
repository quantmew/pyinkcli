"""use-focus-with-id example for pyinkcli."""

from pyinkcli import Box, Text, render, useFocus, useFocusManager, useInput
from pyinkcli.component import createElement


def Item(*, label: str, element_id: str):
    is_focused, _ = useFocus(id=element_id)
    return Box(
        Text(label),
        Text(" (focused)", color="green") if is_focused else Text(""),
    )


def focus_with_id_example():
    focus_manager = useFocusManager()

    def on_input(char, key):
        if char in {"1", "2", "3"}:
            focus_manager.focus(char)

    useInput(on_input)

    return Box(
        Box(
            Text(
                "Press Tab to focus next element, Shift+Tab to focus previous element, Esc to\n"
                "reset focus.",
            ),
            marginBottom=1,
        ),
        createElement(Item, label="Press 1 to focus", element_id="1"),
        createElement(Item, label="Press 2 to focus", element_id="2"),
        createElement(Item, label="Press 3 to focus", element_id="3"),
        flexDirection="column",
        padding=1,
    )


if __name__ == "__main__":
    render(focus_with_id_example).wait_until_exit()
