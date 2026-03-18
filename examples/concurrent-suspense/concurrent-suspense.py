"""concurrent-suspense example for ink-python."""

from __future__ import annotations

import threading
import time

from ink_python import Box, Text, render
from ink_python.component import createElement
from ink_python.hooks import useEffect, useState
from ink_python.suspense_runtime import readResource, resetAllResources


def _fetch_data(name: str, delay: float) -> str:
    return readResource(
        f"examples:concurrent-suspense:{name}:{delay}",
        lambda: (
            time.sleep(delay),
            f'Data for "{name}" (fetched in {int(delay * 1000)}ms)',
        )[1],
    )


def DataItem(name: str, delay: float):
    return Box(Text(_fetch_data(name, delay), color="green"), marginLeft=2)


def Loading(message: str):
    return Box(Text(message, color="yellow"), marginLeft=2)


def Suspense(*children, fallback=None):
    return createElement("__ink-suspense__", *children, fallback=fallback)


def concurrent_suspense_example():
    show_more, set_show_more = useState(False)

    def schedule_more():
        if show_more:
            return None

        cancelled = False

        def worker():
            nonlocal cancelled
            time.sleep(2.0)
            if not cancelled:
                set_show_more(True)

        threading.Thread(target=worker, daemon=True).start()

        def cleanup():
            nonlocal cancelled
            cancelled = True

        return cleanup

    useEffect(schedule_more, (show_more,))

    children = [
        Text("Concurrent Suspense Demo", bold=True, underline=True),
        Text(
            "(With concurrent=True, async data re-renders through the suspense runtime)",
            dimColor=True,
        ),
        Box(),
        Text("Fast data (200ms):"),
        createElement(
            Suspense,
            createElement(DataItem, name="fast", delay=0.2),
            fallback=createElement(Loading, message="Loading fast data..."),
        ),
        Box(),
        Text("Medium data (800ms):"),
        createElement(
            Suspense,
            createElement(DataItem, name="medium", delay=0.8),
            fallback=createElement(Loading, message="Loading medium data..."),
        ),
        Box(),
        Text("Slow data (1500ms):"),
        createElement(
            Suspense,
            createElement(DataItem, name="slow", delay=1.5),
            fallback=createElement(Loading, message="Loading slow data..."),
        ),
    ]

    if show_more:
        children.extend(
            [
                Box(),
                Text("Dynamically added (500ms):"),
                createElement(
                    Suspense,
                    createElement(DataItem, name="dynamic", delay=0.5),
                    fallback=createElement(Loading, message="Loading dynamic data..."),
                ),
            ]
        )

    return Box(*children, flexDirection="column")


if __name__ == "__main__":
    resetAllResources()
    render(concurrent_suspense_example, concurrent=True).wait_until_exit()
