"""cursor-ime example for ink-python."""

from __future__ import annotations

from ink_python import Box, Text, render, useCursor, useInput
from ink_python.hooks import useState
from ink_python.utils.string_width import string_width


def cursor_ime_example():
    text, set_text = useState("")
    cursor = useCursor()

    def on_input(char, key):
        if key.ctrl and char == "c":
            raise KeyboardInterrupt

        if key.backspace or key.delete:
            set_text(lambda previous: previous[:-1])
            return

        if char and not key.ctrl and not key.meta:
            set_text(lambda previous: previous + char)

    useInput(on_input)

    prompt = "> "
    cursor.setCursorPosition({"x": string_width(prompt + text), "y": 1})

    return Box(
        Text("Type Korean (Ctrl+C to exit):"),
        Text(f"{prompt}{text}"),
        flexDirection="column",
    )


if __name__ == "__main__":
    render(cursor_ime_example).wait_until_exit()
