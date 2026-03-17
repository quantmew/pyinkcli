"""
Chat example for ink-python.

Demonstrates a simple chat interface with message input and display.
Port of js_source/ink/examples/chat/chat.tsx
"""

from ink_python import render, Box, Text, use_input


message_id = 0


def chat_app():
    """A simple chat application."""
    from ink_python.hooks import useState

    global message_id
    input_text, set_input = useState("")
    messages, set_messages = useState([])

    def handle_input(char, key):
        global message_id
        if key.return_pressed:
            if input_text:
                set_messages([
                    *messages,
                    {"id": message_id, "text": f"User: {input_text}"},
                ])
                message_id += 1
                set_input("")
        elif key.backspace or key.delete:
            set_input(input_text[:-1])
        elif char:
            set_input(input_text + char)

    use_input(handle_input)

    return Box(
        Box(
            *[Text(message["text"]) for message in messages],
            flexDirection="column",
        ),
        Box(
            Text(f"Enter your message: {input_text}"),
            marginTop=1,
        ),
        flexDirection="column",
        padding=1,
    )


if __name__ == "__main__":
    render(chat_app).wait_until_exit()
