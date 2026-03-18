"""box-backgrounds example for ink-python."""

from ink_python import render, Box, Text, useApp, useInput


def box_backgrounds_example():
    app = useApp()

    def on_input(char, key):
        if char == "q" or (key.ctrl and char == "c"):
            app.exit()

    useInput(on_input)

    return Box(
        Text("Box Background Examples:", bold=True),
        Text("1. Standard red background (10x3):"),
        Box(Text("Hello"), backgroundColor="red", width=10, height=3, alignSelf="flex-start"),
        Text("2. Blue background with border (12x4):"),
        Box(
            Text("Border"),
            backgroundColor="blue",
            borderStyle="round",
            width=12,
            height=4,
            alignSelf="flex-start",
        ),
        Text("3. Green background with padding (14x4):"),
        Box(
            Text("Padding"),
            backgroundColor="green",
            padding=1,
            width=14,
            height=4,
            alignSelf="flex-start",
        ),
        Text("4. Yellow background with center alignment (16x3):"),
        Box(
            Text("Centered"),
            backgroundColor="yellow",
            width=16,
            height=3,
            justifyContent="center",
            alignSelf="flex-start",
        ),
        Text("5. Magenta background, column layout (12x5):"),
        Box(
            Text("Line 1"),
            Text("Line 2"),
            backgroundColor="magenta",
            flexDirection="column",
            width=12,
            height=5,
            alignSelf="flex-start",
        ),
        Text("6. Hex color background #FF8800 (10x3):"),
        Box(
            Text("Hex"),
            backgroundColor="#FF8800",
            width=10,
            height=3,
            alignSelf="flex-start",
        ),
        Text("7. RGB background rgb(0,255,0) (10x3):"),
        Box(
            Text("RGB"),
            backgroundColor="rgb(0,255,0)",
            width=10,
            height=3,
            alignSelf="flex-start",
        ),
        Text("8. Text inheritance test:"),
        Box(
            Text("Inherited "),
            Text("Override ", backgroundColor="red"),
            Text("Back to inherited"),
            backgroundColor="cyan",
            alignSelf="flex-start",
        ),
        Text("9. Nested background inheritance:"),
        Box(
            Text("Outer "),
            Box(
                Text("Inner "),
                Text("Deep", backgroundColor="red"),
                backgroundColor="yellow",
            ),
            backgroundColor="blue",
            alignSelf="flex-start",
        ),
        Text("Press 'q' to exit.", dimColor=True),
        flexDirection="column",
        gap=1,
        padding=1,
    )


if __name__ == "__main__":
    render(box_backgrounds_example).wait_until_exit()
