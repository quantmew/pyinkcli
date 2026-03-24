"""jest example for pyinkcli."""

from __future__ import annotations

import threading
import time

from summary import Summary
from test import Test

from pyinkcli import Box, Static, render
from pyinkcli.component import createElement
from pyinkcli.example_data import JEST_SCHEDULE
from pyinkcli.hooks import useEffect, useState

_SCHEDULE = list(JEST_SCHEDULE)
PATHS = [entry["path"] for entry in _SCHEDULE]
SCHEDULE_BY_PATH = {entry["path"]: entry for entry in _SCHEDULE}


def jest_example():
    completed_tests, set_completed_tests = useState([])
    running_tests, set_running_tests = useState([])
    display_time_ms, set_display_time_ms = useState(0)

    def setup():
        running = True

        def run_scheduler():
            pending = list(_SCHEDULE)
            active: list[dict[str, object]] = []
            started_at = time.monotonic()
            latest_display_ms = 0

            while running and (pending or active):
                now = time.monotonic()

                while pending and len(active) < 4:
                    plan = pending.pop(0)
                    active.append(
                        {
                            "path": plan["path"],
                            "status": "runs",
                            "done_at": now + (plan["delayMs"] / 1000),
                            "final_status": plan["status"],
                        }
                    )

                set_running_tests(
                    [{"status": "runs", "path": test["path"]} for test in active]
                )

                finished = [test for test in active if now >= test["done_at"]]
                if finished:
                    finished_paths = {test["path"] for test in finished}
                    active = [test for test in active if test["path"] not in finished_paths]
                    set_running_tests(
                        [{"status": "runs", "path": test["path"]} for test in active]
                    )
                    set_completed_tests(
                        lambda previous, batch=finished: [
                            *previous,
                            *[
                                {"status": test["final_status"], "path": test["path"]}
                                for test in batch
                            ],
                        ]
                    )
                    latest_display_ms = max(
                        latest_display_ms,
                        max(int((test["done_at"] - started_at) * 1000) for test in finished) + 12,
                    )
                    set_display_time_ms(latest_display_ms)

                time.sleep(0.02)

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
    elapsed_ms = max(display_time_ms, 0)
    duration = f"{elapsed_ms}ms" if elapsed_ms < 1000 else f"{elapsed_ms / 1000:.1f}s"

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
