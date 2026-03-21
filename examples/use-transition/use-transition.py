"""use-transition example for pyinkcli."""

from __future__ import annotations

import time

from pyinkcli import Box, Text, render, useInput
from pyinkcli.hooks import useMemo, useState, useTransition


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


def SearchApp():
    query, set_query = useState("")
    is_pending, start_transition = useTransition()
    deferred_query, set_deferred_query = useState("")

    filtered_items = useMemo(
        lambda: _generate_items(deferred_query),
        (deferred_query,),
    )

    def handle_input(input_char, key) -> None:
        if key.backspace or key.delete:
            set_query(lambda previous: previous[:-1])
            start_transition(
                lambda: set_deferred_query(lambda previous: previous[:-1])
            )
            return

        if input_char and not key.ctrl and not key.meta:
            set_query(lambda previous: previous + input_char)
            start_transition(
                lambda: set_deferred_query(lambda previous: previous + input_char)
            )

    useInput(handle_input)

    result_children = [
        Text(
            item,
            dimColor=is_pending,
            key=item,
        )
        for item in filtered_items
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
        Box(marginTop=1),
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
    render(SearchApp, concurrent=True).wait_until_exit()
