"""jest example for pyinkcli."""

from __future__ import annotations

import random
import threading
import time

from pyinkcli import Box, Static, render
from pyinkcli.component import createElement
from pyinkcli.hooks import useEffect, useState

from summary import Summary
from test import Test


PATHS = [
    "tests/login.js",
    "tests/signup.js",
    "tests/forgot-password.js",
    "tests/reset-password.js",
    "tests/view-profile.js",
    "tests/edit-profile.js",
    "tests/delete-profile.js",
    "tests/posts.js",
    "tests/post.js",
    "tests/comments.js",
]


def jest_example():
    start_time = useState(lambda: time.time())[0]
    completed_tests, set_completed_tests = useState([])
    running_tests, set_running_tests = useState([])

    def setup():
        running = True

        def run_scheduler():
            pending_paths = list(PATHS)
            active_tests: list[dict[str, object]] = []

            while running and (pending_paths or active_tests):
                now = time.time()

                while pending_paths and len(active_tests) < 4:
                    path = pending_paths.pop(0)
                    active_tests.append(
                        {
                            "path": path,
                            "status": "runs",
                            "done_at": now + 0.15 + random.random() * 0.45,
                            "final_status": "pass" if random.random() < 0.5 else "fail",
                        }
                    )

                set_running_tests(
                    [
                        {"status": "runs", "path": test["path"]}
                        for test in active_tests
                    ]
                )

                finished_paths: list[str] = []
                completed_batch: list[dict[str, str]] = []
                for test in active_tests:
                    if now >= test["done_at"]:
                        finished_paths.append(test["path"])
                        completed_batch.append(
                            {
                                "status": test["final_status"],
                                "path": test["path"],
                            }
                        )

                if finished_paths:
                    active_tests = [
                        test for test in active_tests if test["path"] not in finished_paths
                    ]
                    set_running_tests(
                        [
                            {"status": "runs", "path": test["path"]}
                            for test in active_tests
                        ]
                    )
                    set_completed_tests(
                        lambda previous: [*previous, *completed_batch]
                    )

                time.sleep(0.05)

            if running:
                set_running_tests([])

        thread = threading.Thread(target=run_scheduler, daemon=True)
        thread.start()

        def cleanup():
            nonlocal running
            running = False

        return cleanup

    useEffect(setup, ())

    passed = len([test for test in completed_tests if test["status"] == "pass"])
    failed = len([test for test in completed_tests if test["status"] == "fail"])
    duration = f"{time.time() - start_time:.1f}s"

    return Box(
        Static(
            lambda test, _: createElement(
                Test,
                status=test["status"],
                path=test["path"],
            ),
            items=completed_tests,
        ),
        Box(
            *[
                createElement(
                    Test,
                    key=test["path"],
                    status=test["status"],
                    path=test["path"],
                )
                for test in running_tests
            ],
            flexDirection="column",
            marginTop=1,
        )
        if running_tests
        else Box(),
        createElement(
            Summary,
            is_finished=len(completed_tests) == len(PATHS) and len(running_tests) == 0,
            passed=passed,
            failed=failed,
            time_text=duration,
        ),
        flexDirection="column",
    )


if __name__ == "__main__":
    render(jest_example).wait_until_exit()
