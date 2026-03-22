#!/usr/bin/env python3
"""
Performance comparison test - Sync vs Concurrent mode.

This script runs the same workload in both sync and concurrent modes
to demonstrate the difference in responsiveness.

Run with:
    python stress-test-compare.py --items 500
"""

from __future__ import annotations

import argparse
import random
import threading
import time
from typing import Any

from pyinkcli import Box, Text, render, useInput
from pyinkcli.hooks import useEffect, useState, useTransition
from perf_metrics import PerfMetricCollector, use_perf_metrics


SYNC_COLOR = "red"
CONCURRENT_COLOR = "green"
_PERF_COLLECTOR = PerfMetricCollector()


def _generate_data(count: int) -> list[dict[str, Any]]:
    return [
        {
            "id": i,
            "value": random.randint(1, 1000),
            "category": random.choice(["A", "B", "C", "D"]),
        }
        for i in range(count)
    ]


def _expensive_transform(
    items: list[dict[str, Any]],
    multiplier: int,
    delay_per_item_ms: float = 2,
) -> list[dict[str, Any]]:
    result = []
    for item in items:
        if delay_per_item_ms > 0:
            start = time.time()
            target = delay_per_item_ms / 1000.0
            while time.time() - start < target:
                _ = item["value"] * 1.001

        computed = (item["value"] * multiplier) % 10000
        result.append(
            {
                **item,
                "computed": round(computed, 2),
                "category_label": f"Cat-{item['category']}",
            }
        )
    return result


def DualModeApp(num_items: int, delay_per_item_ms: float):
    base_items, set_base_items = useState(lambda: _generate_data(num_items))

    sync_multiplier, set_sync_multiplier = useState(1)
    sync_result = _expensive_transform(base_items, sync_multiplier, delay_per_item_ms)

    concurrent_multiplier, set_concurrent_multiplier = useState(1)
    deferred_multiplier, set_deferred_multiplier = useState(1)
    is_pending, start_transition = useTransition()
    performance_metrics = use_perf_metrics(useEffect, useState, _PERF_COLLECTOR)

    concurrent_result = _expensive_transform(
        base_items,
        deferred_multiplier,
        delay_per_item_ms * 0.5,
    )

    def sync_deferred_multiplier() -> None:
        set_deferred_multiplier(concurrent_multiplier)

    useEffect(sync_deferred_multiplier, (concurrent_multiplier,))

    def setup_auto_update():
        running = True

        def update_loop():
            nonlocal running
            while running:
                time.sleep(1.0)
                set_sync_multiplier(lambda m: (m % 100) + 1)
                start_transition(lambda: set_concurrent_multiplier(lambda m: (m % 100) + 1))

        thread = threading.Thread(target=update_loop, daemon=True)
        thread.start()

        def cleanup():
            nonlocal running
            running = False

        return cleanup

    useEffect(setup_auto_update, ())

    def handle_input(char, key):
        if key.enter:
            set_sync_multiplier(lambda m: m + 1)
            start_transition(lambda: set_concurrent_multiplier(lambda m: m + 1))
        elif char == "r":
            set_base_items(_generate_data(num_items))
        elif key.up_arrow:
            set_sync_multiplier(lambda m: m + 1)
        elif key.down_arrow:
            start_transition(lambda: set_concurrent_multiplier(lambda m: m + 1))

    useInput(handle_input)

    sync_visible = sync_result[:15]
    concurrent_visible = concurrent_result[:15]

    def build_rows(items, color):
        return [
            Text(
                f"  {item['id']:04d} | {item['value']:4d} | {item['computed']:>10.2f} | {item['category_label']}",
                color=color,
            )
            for item in items
        ]

    sync_status = (
        "Sync (immediate)" if sync_multiplier == deferred_multiplier else "Sync (processing)"
    )
    concurrent_status = f"Concurrent {('[PENDING]' if is_pending else '[DONE]')}"

    return Box(
        Box(
            Text(" Performance Comparison: SYNC vs CONCURRENT ", bold=True, reverse=True),
            Text(f"  |  Items: {num_items}  |  Work/item: {delay_per_item_ms}ms", dimColor=True),
            Text(
                f"  |  FPS: {performance_metrics['fps']:.1f}  |  Render: {performance_metrics['render_time_ms']:.1f}ms",
                dimColor=True,
            ),
            flexDirection="column",
        ),
        Box(marginTop=1),
        Box(
            Box(
                Text(" SYNC MODE ", bold=True, color=SYNC_COLOR, reverse=True),
                Text(f"  {sync_status}", dimColor=True),
                flexDirection="row",
                width=48,
            ),
            Box(
                Text(" CONCURRENT MODE ", bold=True, color=CONCURRENT_COLOR, reverse=True),
                Text(f"  {concurrent_status}", dimColor=True),
                flexDirection="row",
                width=48,
            ),
            flexDirection="row",
        ),
        Box(
            Box(
                Text(" ID   | Value | Computed   | Cat", bold=True, underline=True, dimColor=True),
                width=48,
            ),
            Box(
                Text(" ID   | Value | Computed   | Cat", bold=True, underline=True, dimColor=True),
                width=48,
            ),
            flexDirection="row",
        ),
        *[
            Box(
                Box(
                    *build_rows(
                        [sync_visible[i]] if i < len(sync_visible) else [],
                        SYNC_COLOR,
                    ),
                    flexDirection="column",
                    width=48,
                ) if i < len(sync_visible) else Box(Text("", width=48)),
                Box(
                    *build_rows(
                        [concurrent_visible[i]] if i < len(concurrent_visible) else [],
                        CONCURRENT_COLOR,
                    ),
                    flexDirection="column",
                    width=48,
                ) if i < len(concurrent_visible) else Box(Text("", width=48)),
                flexDirection="row",
            )
            for i in range(15)
        ],
        Box(marginTop=1),
        Box(
            Text(" Controls: ", bold=True),
            Text("↑: Sync update | ↓: Concurrent update | Enter: Both | R: Refresh", dimColor=True),
            flexDirection="column",
        ),
        Box(
            Text(" Note: In SYNC mode, each update blocks the UI. ", color=SYNC_COLOR),
            Text(" In CONCURRENT mode, updates can be interrupted. ", color=CONCURRENT_COLOR),
            flexDirection="column",
            marginTop=1,
        ),
        flexDirection="column",
    )


def main():
    parser = argparse.ArgumentParser(description="Compare sync vs concurrent performance")
    parser.add_argument("--items", type=int, default=300, help="Number of items (default: 300)")
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Artificial delay per item in ms (default: 2.0)",
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print(" SYNC vs CONCURRENT PERFORMANCE COMPARISON")
    print("=" * 60)
    print(f" Items: {args.items}")
    print(f" Delay per item: {args.delay}ms")
    print(f" Total compute time per update: ~{args.items * args.delay:.0f}ms")
    print("\n LEFT side:  Sync mode (blocks on every update)")
    print(" RIGHT side: Concurrent mode (interruptible updates)")
    print("=" * 60 + "\n")

    def app():
        return DualModeApp(num_items=args.items, delay_per_item_ms=args.delay)

    _PERF_COLLECTOR.reset()
    render(app, concurrent=True, on_render=_PERF_COLLECTOR.record_render).wait_until_exit()


if __name__ == "__main__":
    main()
