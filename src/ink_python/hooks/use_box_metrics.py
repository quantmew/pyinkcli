"""
useBoxMetrics hook for ink-python.

This hook provides box layout metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from ink_python.hooks.use_stdout import use_stdout

if TYPE_CHECKING:
    from ink_python.dom import DOMElement


@dataclass
class BoxMetrics:
    """Metrics of a box element."""

    width: int = 0
    height: int = 0
    left: int = 0
    top: int = 0


@dataclass
class UseBoxMetricsResult(BoxMetrics):
    """Result of useBoxMetrics hook."""

    has_measured: bool = False


def use_box_metrics(ref: dict) -> UseBoxMetricsResult:
    """
    A React hook that returns the current layout metrics for a tracked box element.

    It updates when layout changes (for example terminal resize, sibling/content
    changes, or position changes).

    The hook returns `{width: 0, height: 0, left: 0, top: 0}` until the first
    layout pass completes. It also returns zeros when the tracked ref is detached.

    Use `has_measured` to detect when the currently tracked element has been measured.

    Args:
        ref: A ref object containing the DOM element.

    Returns:
        UseBoxMetricsResult: Box metrics with has_measured flag.

    Example:
        >>> ref = {"current": None}
        >>> metrics = use_box_metrics(ref)
        >>> if metrics.has_measured:
        ...     print(f"{metrics.width}x{metrics.height} at {metrics.left},{metrics.top}")
    """
    stdout = use_stdout()

    if ref.get("current") is None:
        return UseBoxMetricsResult()

    element: DOMElement = ref["current"]
    yoga_node = getattr(element, "yoga_node", None)

    if yoga_node is None:
        return UseBoxMetricsResult()

    try:
        width = int(yoga_node.get_computed_width())
        height = int(yoga_node.get_computed_height())
        left = int(yoga_node.get_computed_left())
        top = int(yoga_node.get_computed_top())

        return UseBoxMetricsResult(
            width=width,
            height=height,
            left=left,
            top=top,
            has_measured=True,
        )
    except Exception:
        return UseBoxMetricsResult()


# Alias for camelCase preference
useBoxMetrics = use_box_metrics
