"""
Static example for pyinkcli.

Closer to js_source/ink/examples/static/static.tsx.
Appends completed tests to Static output and keeps a live counter below.
"""

import threading

from pyinkcli import Box, Static, Text
from pyinkcli.example_runner import run_example
from pyinkcli.hooks import useEffect, useState


def static_example():
    """Render incrementally completed tests using Static."""
    tests, set_tests = useState([])

    def setup_runner():
        running = True
        timer = None
        completed_tests = 0

        def run():
            nonlocal timer, completed_tests
            if not running or completed_tests >= 10:
                return
            test_id = completed_tests
            completed_tests += 1
            set_tests(
                lambda previous, index=test_id: [
                    *previous,
                    {"id": index, "title": f"Test #{index + 1}"},
                ]
            )
            if running and completed_tests < 10:
                timer = threading.Timer(0.24, run)
                timer.daemon = True
                timer.start()

        run()

        def cleanup():
            nonlocal running, timer
            running = False
            if timer is not None:
                timer.cancel()

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
    run_example(static_example, patch_console=False)
