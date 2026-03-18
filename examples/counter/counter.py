#!/usr/bin/env python3
"""
Counter example for ink-python.

Port of js_source/ink/examples/counter/counter.tsx.
Displays an auto-incrementing counter.
"""

import threading
import time

from ink_python import render, Text
from ink_python.hooks import useState, useEffect


def counter_example():
    """Render an auto-incrementing counter."""
    counter, set_counter = useState(0)

    def setup_timer():
        running = True

        def tick():
            while running:
                time.sleep(0.1)
                set_counter(lambda value: value + 1)

        thread = threading.Thread(target=tick, daemon=True)
        thread.start()

        def cleanup():
            nonlocal running
            running = False

        return cleanup

    useEffect(setup_timer, ())
    return Text(f"{counter} tests passed", color="green")


if __name__ == "__main__":
    render(counter_example).wait_until_exit()
