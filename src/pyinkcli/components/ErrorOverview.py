"""Error overview component matching JS `components/ErrorOverview.tsx`."""

from __future__ import annotations

from typing import Optional

from pyinkcli._component_runtime import RenderableNode
from pyinkcli.components.Box import Box
from pyinkcli.components.Text import Text


def ErrorOverview(*, error: Exception) -> RenderableNode:
    message = str(error) or error.__class__.__name__
    stack = getattr(error, "__traceback__", None)
    lines: list[str] = []
    if stack is not None:
        import traceback

        lines = traceback.format_tb(stack)

    children: list[RenderableNode] = [
        Box(
            Text(" ERROR ", background_color="red", color="white"),
            Text(f" {message}"),
        )
    ]

    if lines:
        children.append(
            Box(
                *[
                    Box(
                        Text("- ", dim_color=True),
                        Text(line.rstrip(), dim_color=True),
                    )
                    for line in lines
                ],
                marginTop=1,
                flexDirection="column",
            )
        )

    return Box(
        *children,
        flexDirection="column",
        padding=1,
    )


__all__ = ["ErrorOverview"]
