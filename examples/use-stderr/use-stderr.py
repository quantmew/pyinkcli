"""
Use stderr example for pyinkcli.

Port of js_source/ink/examples/use-stderr/use-stderr.tsx.
Writes to stderr periodically while rendering normal UI.
"""

import threading
import time

from pyinkcli import Text, render, useStderr
from pyinkcli.hooks import useEffect


def use_stderr_example():
    """Render text while periodically writing to stderr."""
    stderr = useStderr()

    def setup_timer():
        running = True

        def tick():
            while running:
                time.sleep(1)
                stderr.write("Hello from Ink to stderr\n")

        thread = threading.Thread(target=tick, daemon=True)
        thread.start()

        def cleanup():
            nonlocal running
            running = False

        return cleanup

    useEffect(setup_timer, ())
    return Text("Hello World")


if __name__ == "__main__":
    render(use_stderr_example).wait_until_exit()
