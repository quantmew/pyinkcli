"""aria example for pyinkcli."""

from pyinkcli import Box, Text, render, useInput
from pyinkcli.hooks import useState


def aria_example():
    checked, set_checked = useState(False)

    def on_input(char, _key):
        if char == " ":
            set_checked(lambda current: not current)

    useInput(on_input)

    return Box(
        Text(
            "Press spacebar to toggle the checkbox. This example is best experienced "
            "with a screen reader."
        ),
        Box(
            Box(
                Text("[x]" if checked else "[ ]"),
                aria_role="checkbox",
                aria_state={"checked": checked},
            ),
            marginTop=1,
        ),
        Box(
            Text("This text is hidden from screen readers.", aria_hidden=True),
            marginTop=1,
        ),
        flexDirection="column",
    )


if __name__ == "__main__":
    render(aria_example, is_screen_reader_enabled=True).wait_until_exit()
