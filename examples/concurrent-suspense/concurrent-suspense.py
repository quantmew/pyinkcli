"""concurrent-suspense example for pyinkcli."""

from __future__ import annotations

import threading
import time

from pyinkcli import Box, Text, render
from pyinkcli.component import createElement
from pyinkcli.hooks import useEffect, useState
from pyinkcli.suspense_runtime import readResource, resetAllResources


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

    useEffect(schedule_more, ())

    children = [
        Text("Concurrent Suspense Demo", bold=True, underline=True),
        Text(
            "(With concurrent: true, Suspense re-renders automatically)",
            dimColor=True,
        ),
        Box(marginTop=1),
        Text("Fast data (200ms):"),
        createElement(
            Suspense,
            createElement(DataItem, name="fast", delay=0.2),
            fallback=createElement(Loading, message="Loading fast data..."),
        ),
        Box(marginTop=1),
        Text("Medium data (800ms):"),
        createElement(
            Suspense,
            createElement(DataItem, name="medium", delay=1.0),
            fallback=createElement(Loading, message="Loading medium data..."),
        ),
        Box(marginTop=1),
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
                Box(marginTop=1),
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
