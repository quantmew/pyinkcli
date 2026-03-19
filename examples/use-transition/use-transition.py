"""use-transition example for pyinkcli."""

from __future__ import annotations

import time

from pyinkcli import Box, Text, render, useInput
from pyinkcli.components._app_context_runtime import _get_app_context
from pyinkcli.hooks import useMemo, useState


def _generate_items(filter_text: str) -> list[str]:
    all_items = [
        f"Item {index + 1}: {['Apple', 'Banana', 'Cherry', 'Date', 'Elderberry'][index % 5]}"
        for index in range(200)
    ]

    if not filter_text:
        return all_items[:10]

    start = time.time()
    while time.time() - start < 0.1:
        pass

    lowered = filter_text.lower()
    return [
        item for item in all_items if lowered in item.lower()
    ][:10]


def useTransition():
    is_pending, set_is_pending = useState(False)
    app_context = _get_app_context()

    def start_transition(callback):
        is_concurrent = bool(
            app_context is not None
            and getattr(getattr(app_context, "app", None), "is_concurrent", False)
        )
        if not is_concurrent:
            callback()
            return

        set_is_pending(True)
        scheduler = getattr(app_context, "schedule_transition", None) if app_context else None
        if callable(scheduler):
            scheduler(
                callback,
                lambda is_latest: set_is_pending(False) if is_latest else None,
                0.05,
            )
            return

        callback()
        set_is_pending(False)

    return is_pending, start_transition


def use_transition_example():
    query, set_query = useState("")
    deferred_query, set_deferred_query = useState("")
    is_pending, start_transition = useTransition()

    filtered_items = useMemo(
        lambda: _generate_items(deferred_query),
        (deferred_query,),
    )

    def on_input(char, key):
        if key.ctrl and char == "c":
            raise KeyboardInterrupt

        if key.backspace or key.delete:
            set_query(lambda previous: previous[:-1])
            start_transition(lambda: set_deferred_query(lambda previous: previous[:-1]))
            return

        if char and not key.ctrl and not key.meta:
            set_query(lambda previous: previous + char)
            start_transition(lambda: set_deferred_query(lambda previous: previous + char))

    useInput(on_input)

    result_children = [
        Text(
            item,
            dimColor=is_pending,
            key=f"item-{index}",
        )
        for index, item in enumerate(filtered_items)
    ]

    if not result_children:
        result_children = [Text(" No items found", dimColor=True)]

    results_label = (
        f'Results for "{deferred_query}":'
        if deferred_query
        else "Results (showing first 10):"
    )

    return Box(
        Text("useTransition Demo", bold=True, underline=True),
        Text("(Type to search - input stays responsive while list updates)", dimColor=True),
        Box(),
        Box(
            Text("Search: "),
            Text(query or "(type something)", color="cyan"),
            Text(" (updating...)", color="yellow") if is_pending else None,
        ),
        Box(
            Text(results_label, bold=True),
            *result_children,
            flexDirection="column",
            marginTop=1,
        ),
        Box(Text("Press Ctrl+C to exit", dimColor=True), marginTop=1),
        flexDirection="column",
    )


if __name__ == "__main__":
    render(use_transition_example, concurrent=True).wait_until_exit()
