"""
Select Input example for ink-python.

Demonstrates a selectable list with keyboard navigation.
Port of js_source/ink/examples/select-input/select-input.tsx
"""

from ink_python import render, Box, Text, use_input, use_is_screen_reader_enabled


ITEMS = ["Red", "Green", "Blue", "Yellow", "Magenta", "Cyan"]


def select_input_example():
    """Render a selectable list."""
    from ink_python.hooks import useState

    selected_index, set_selected_index = useState(0)
    is_screen_reader_enabled = use_is_screen_reader_enabled()

    def handle_input(char, key):
        if key.up_arrow:
            set_selected_index(selected_index - 1 if selected_index > 0 else len(ITEMS) - 1)
        elif key.down_arrow:
            set_selected_index(selected_index + 1 if selected_index < len(ITEMS) - 1 else 0)
        elif is_screen_reader_enabled and char:
            try:
                number = int(char)
                if 0 < number <= len(ITEMS):
                    set_selected_index(number - 1)
            except ValueError:
                pass

    use_input(handle_input)

    items = []
    for index, item in enumerate(ITEMS):
        is_selected = index == selected_index
        label = f"> {item}" if is_selected else f"  {item}"
        screen_reader_label = f"{index + 1}. {item}"
        items.append(
            Box(
                Text(
                    screen_reader_label if is_screen_reader_enabled else label,
                    color="blue" if is_selected else None,
                )
            )
        )

    return Box(
        Text("Select a color:"),
        *items,
        flexDirection="column",
    )


if __name__ == "__main__":
    render(select_input_example).wait_until_exit()
