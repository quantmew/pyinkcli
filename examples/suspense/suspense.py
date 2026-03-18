"""suspense example for ink-python."""

from __future__ import annotations

import time

from ink_python import Text, render
from ink_python.component import createElement
from ink_python.suspense_runtime import readResource, resetResource


def _read_message() -> str:
    return readResource(
        "examples:suspense:hello-world",
        lambda: (time.sleep(0.5), "Hello World")[1],
    )


def Example():
    return Text(_read_message())


def Fallback():
    return Text("Loading...")


def Suspense(*children, fallback=None):
    return createElement("__ink-suspense__", *children, fallback=fallback)


def suspense_example():
    return createElement(
        Suspense,
        createElement(Example),
        fallback=createElement(Fallback),
    )


if __name__ == "__main__":
    resetResource("examples:suspense:hello-world")
    render(suspense_example).wait_until_exit()
