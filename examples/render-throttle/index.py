"""render-throttle example for ink-python."""

import threading
import time

from ink_python import render, Box, Text
from ink_python.hooks import useEffect, useState


def app():
    count, set_count = useState(0)

    def setup():
        running = True

        def tick():
            while running:
                time.sleep(0.01)
                set_count(lambda value: value + 1)

        thread = threading.Thread(target=tick, daemon=True)
        thread.start()

        def cleanup():
            nonlocal running
            running = False

        return cleanup

    useEffect(setup, ())

    return Box(
        Text(f"Counter: {count}"),
        Text("This updates every 10ms but renders are throttled."),
        Text("Press Ctrl+C to exit.", dimColor=True),
        flexDirection="column",
        padding=1,
    )


if __name__ == "__main__":
    render(app, max_fps=10).wait_until_exit()
