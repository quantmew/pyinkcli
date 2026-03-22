"""
Static example for pyinkcli.

Closer to js_source/ink/examples/static/static.tsx.
Appends completed tests to Static output and keeps a live counter below.
"""

import threading
import time

from pyinkcli import Box, Static, Text, render
from pyinkcli.hooks import useEffect, useState


def static_example():
    """Render incrementally completed tests using Static."""
    tests, set_tests = useState([])

    def setup_runner():
        running = True

        def run_tests():
            completed = 0
            while running and completed < 10:
                time.sleep(0.1)
                completed += 1
                test_id = completed - 1
                set_tests(
                    lambda previous, index=test_id: [
                        *previous,
                        {"id": index, "title": f"Test #{index + 1}"},
                    ]
                )

        thread = threading.Thread(target=run_tests, daemon=True)
        thread.start()

        def cleanup():
            nonlocal running
            running = False

        return cleanup

    useEffect(setup_runner, ())
    return Box(
        Static(
            lambda test, _: Box(
                Text(f"✔ {test['title']}", color="green")
            ),
            items=tests,
        ),
        Box(
            Text(f"Completed tests: {len(tests)}", dimColor=True),
            marginTop=1,
        ),
        flexDirection="column",
    )


if __name__ == "__main__":
    render(static_example, interactive=True, patch_console=False).wait_until_exit()
