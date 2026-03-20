"""
Use Stdout example for pyinkcli.

Demonstrates the useStdout hook to inspect stdout dimensions.
Based on js_source/ink/examples/use-stdout/use-stdout.tsx
"""

import threading
import time

from pyinkcli import Box, Text, render, useStdout
from pyinkcli.hooks import useEffect


def use_stdout_example():
    """Render stdout dimensions."""
    stdout = useStdout()

    def setup_timer():
        running = True

        def tick():
            while running:
                time.sleep(1)
                stdout.write("Hello from Ink to stdout\n")

        thread = threading.Thread(target=tick, daemon=True)
        thread.start()

        def cleanup():
            nonlocal running
            running = False

        return cleanup

    useEffect(setup_timer, ())

    return Box(
        Box(
            Text("Terminal dimensions:", bold=True, underline=True),
            Box(
                Text("Width: "),
                Text(str(stdout.columns), bold=True),
                marginTop=1,
            ),
            Box(
                Text("Height: "),
                Text(str(stdout.rows), bold=True),
            ),
            flexDirection="column",
        ),
        paddingX=2,
        paddingY=1,
        flexDirection="column",
    )


if __name__ == "__main__":
    render(use_stdout_example).wait_until_exit()
