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
from pyinkcli.hooks import useMemo, useState, useTransition


# Colors for visual distinction
SYNC_COLOR = "red"
CONCURRENT_COLOR = "green"


def _generate_data(count: int) -> list[dict[str, Any]]:
    """Generate test data."""
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
    """
    Expensive transformation - simulates real-world heavy computation.

    Args:
        items: Input items
        multiplier: Calculation multiplier
        delay_per_item_ms: Artificial delay per item (ms) - controls how "heavy" the computation is
    """
    result = []
    for item in items:
        # Busy wait to simulate work
        if delay_per_item_ms > 0:
            start = time.time()
            target = delay_per_item_ms / 1000.0
            while time.time() - start < target:
                # Simulate work
                _ = item["value"] * 1.001

        computed = (item["value"] * multiplier) % 10000
        result.append({
            **item,
            "computed": round(computed, 2),
            "category_label": f"Cat-{item['category']}",
        })
    return result


def DualModeApp(num_items: int, delay_per_item_ms: float):
    """
    App that shows both sync and concurrent rendering side by side.

    The LEFT side uses regular useState (sync).
    The RIGHT side uses useTransition (concurrent).
    """

    # Shared base data
    base_items, set_base_items = useState(lambda: _generate_data(num_items))

    # Sync side state
    sync_multiplier, set_sync_multiplier = useState(1)
    sync_result = _expensive_transform(base_items, sync_multiplier, delay_per_item_ms)

    # Concurrent side state
    concurrent_multiplier, set_concurrent_multiplier = useState(1)
    deferred_multiplier, set_deferred_multiplier = useState(1)
    is_pending, start_transition = useTransition()

    # Use deferred multiplier for expensive computation
    concurrent_result = _expensive_transform(
        base_items,
        deferred_multiplier,
        delay_per_item_ms * 0.5,  # Slightly less delay for fair comparison
    )

    # FPS counter
    fps_ref = {"frames": 0, "last_time": time.time(), "fps": 0}
    fps_ref["frames"] += 1
    now = time.time()
    if now - fps_ref["last_time"] >= 1.0:
        fps_ref["fps"] = fps_ref["frames"] / (now - fps_ref["last_time"])
        fps_ref["frames"] = 0
        fps_ref["last_time"] = now

    # Auto-update trigger
    from pyinkcli.hooks import useEffect

    def setup_auto_update():
        running = True

        def update_loop():
            nonlocal running
            while running:
                time.sleep(1.0)

                # Trigger updates on both sides
                set_sync_multiplier(lambda m: (m % 100) + 1)
                start_transition(lambda: set_concurrent_multiplier(lambda m: (m % 100) + 1))

        thread = threading.Thread(target=update_loop, daemon=True)
        thread.start()
        return lambda: setattr(thread, "running", False)

    useEffect(setup_auto_update, [])

    # Manual controls
    def handle_input(char, key):
        if key.enter:
            # Sync: immediate update
            set_sync_multiplier(lambda m: m + 1)
            # Concurrent: transition update
            start_transition(lambda: set_concurrent_multiplier(lambda m: m + 1))
        elif char == "r":
            set_base_items(_generate_data(num_items))
        elif key.up_arrow:
            set_sync_multiplier(lambda m: m + 1)
        elif key.down_arrow:
            start_transition(lambda: set_concurrent_multiplier(lambda m: m + 1))

    useInput(handle_input)

    # Calculate stats
    sync_visible = sync_result[:15]
    concurrent_visible = concurrent_result[:15]

    # Build item rows
    def build_rows(items, color):
        rows = []
        for item in items:
            rows.append(
                Text(
                    f"  {item['id']:04d} | {item['value']:4d} | {item['computed']:>10.2f} | {item['category_label']}",
                    color=color,
                )
            )
        return rows

    # Mode indicators
    sync_status = f"Sync (immediate)" if sync_multiplier == deferred_multiplier else "Sync (processing)"
    concurrent_status = (
        f"Concurrent {('[PENDING]' if is_pending else '[DONE]')}"
    )

    return Box(
        # Header
        Box(
            Text(" Performance Comparison: SYNC vs CONCURRENT ", bold=True, reverse=True),
            Text(f"  |  Items: {num_items}  |  Work/item: {delay_per_item_ms}ms", dimColor=True),
            Text(f"  |  FPS: {fps_ref['fps']:.1f}", dimColor=True),
            flexDirection="column",
        ),

        Box(marginTop=1),

        # Side by side headers
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

        # Column headers
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

        # Data rows
        *[
            Box(
                Box(*build_rows([sync_visible[i] if i < len(sync_visible) else {"id": 0, "value": 0, "computed": 0, "category_label": ""}], SYNC_COLOR), flexDirection="column", width=48) if i < len(sync_visible) else Box(Text("", width=48)),
                Box(*build_rows([concurrent_visible[i] if i < len(concurrent_visible) else {"id": 0, "value": 0, "computed": 0, "category_label": ""}], CONCURRENT_COLOR), flexDirection="column", width=48) if i < len(concurrent_visible) else Box(Text("", width=48)),
                flexDirection="row",
            )
            for i in range(15)
        ],

        Box(marginTop=1),

        # Controls
        Box(
            Text(" Controls: ", bold=True),
            Text("↑: Sync update | ↓: Concurrent update | Enter: Both | R: Refresh", dimColor=True),
            flexDirection="column",
        ),

        # Explanation
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
    parser.add_argument(
        "--items",
        type=int,
        default=300,
        help="Number of items (default: 300)",
    )
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
        return DualModeApp(
            num_items=args.items,
            delay_per_item_ms=args.delay,
        )

    render(app, concurrent=True).wait_until_exit()


if __name__ == "__main__":
    main()
