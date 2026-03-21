#!/usr/bin/env python3
"""
Extreme stress test - Demonstrates UI freezing with many components.

This example specifically demonstrates the freezing issue when:
1. There are many components (1000+ items)
2. Each component has expensive computation
3. Updates happen frequently

This will show noticeable lag/freezing, especially in sync mode.
Compare with concurrent mode to see the difference.

Run with:
    python stress-test-extreme.py                 # Default: 1000 items, sync
    python stress-test-extreme.py --items 2000    # 2000 items
    python stress-test-extreme.py --concurrent    # Enable concurrent mode
"""

from __future__ import annotations

import argparse
import random
import threading
import time
from typing import Any

from pyinkcli import Box, Text, render, useInput
from pyinkcli.hooks import useEffect, useMemo, useState, useTransition


# Simulate VERY expensive computation (intentionally slow)
def _expensive_computation(items: list[dict[str, Any]], multiplier: int) -> list[dict[str, Any]]:
    """
    This is INTENTIONALLY slow to demonstrate the freezing problem.
    In real apps, this could be:
    - Complex data transformations
    - Sorting large lists
    - Formatting dates/numbers
    - Image processing
    """
    result = []
    for item in items:
        # Simulate expensive work - 5ms per item = 5 seconds for 1000 items!
        start = time.time()
        computed = item["value"] * multiplier
        # Busy wait to simulate work
        while time.time() - start < 0.005:  # 5ms per item
            computed = (computed * 1.0001) % 10000

        result.append({
            **item,
            "computed_value": round(computed, 4),
            "hash": hash(f"{item['id']}-{computed}") % 100000,
        })
    return result


def ExtremeStressApp(num_items: int, concurrent_mode: bool):
    """App designed to demonstrate freezing."""

    # Initial state
    items, set_items = useState(lambda: [
        {
            "id": i,
            "value": random.randint(1, 100),
            "label": f"Component_{i:05d}",
            "active": random.choice([True, False]),
        }
        for i in range(num_items)
    ])

    multiplier, set_multiplier = useState(1)
    selected_id, set_selected_id = useState(0)
    frame_count, set_frame_count = useState(0)
    last_fps_time, set_last_fps_time = useState(time.time())
    fps, set_fps = useState(0.0)

    # For measuring render time
    render_times_ref = {"times": [], "last_log": time.time()}

    is_pending, start_transition = useTransition()

    # Auto-update: trigger new computation every 500ms
    def setup_auto_update():
        running = True

        def update_loop():
            nonlocal running
            while running:
                time.sleep(0.5)

                # Update random values to trigger re-render
                def update_fn(current_items):
                    new_items = []
                    for item in current_items:
                        if random.random() < 0.1:  # 10% chance to update each item
                            new_item = item.copy()
                            new_item["value"] = random.randint(1, 100)
                            new_item["active"] = random.choice([True, False])
                            new_items.append(new_item)
                        else:
                            new_items.append(item.copy())
                    return new_items

                start_transition(lambda: set_items(update_fn))
                start_transition(lambda: set_multiplier(lambda m: (m % 100) + 1))

        thread = threading.Thread(target=update_loop, daemon=True)
        thread.start()

        return lambda: setattr(thread, "running", False)

    useEffect(setup_auto_update, [])

    # FPS counter
    current_frame = frame_count + 1
    set_frame_count(current_frame)

    now = time.time()
    if now - last_fps_time >= 1.0:
        elapsed = now - last_fps_time
        calculated_fps = current_frame / elapsed
        set_fps(calculated_fps)
        set_frame_count(0)
        set_last_fps_time(now)

        # Log render performance
        render_times_ref["times"].append({
            "time": now,
            "fps": calculated_fps,
            "pending": is_pending,
        })
        # Keep only last 10 entries
        render_times_ref["times"] = render_times_ref["times"][-10:]

    # KEY: This expensive computation runs on EVERY render
    # This is what causes the freeze!
    computed_items = useMemo(
        lambda: _expensive_computation(items, multiplier),
        (id(items), multiplier),  # Re-compute when items identity or multiplier changes
    )

    # Keyboard input
    def handle_key(char, key):
        if key.up_arrow:
            set_selected_id(max(0, selected_id - 1))
        elif key.down_arrow:
            set_selected_id(min(num_items - 1, selected_id + 1))
        elif key.enter:
            # Manual trigger - causes full re-computation
            start_transition(lambda: set_multiplier(lambda m: m + 1))

    useInput(handle_key)

    # Determine visible range
    visible_start = max(0, selected_id - 15)
    visible_end = min(num_items, visible_start + 30)
    visible_items = computed_items[visible_start:visible_end]

    # Build status indicator
    if fps > 30:
        fps_color = "green"
        fps_status = "GOOD"
    elif fps > 10:
        fps_color = "yellow"
        fps_status = "LAGGY"
    else:
        fps_color = "red"
        fps_status = "FREEZING!"

    # Build item display
    item_displays = []
    for i, item in enumerate(visible_items):
        actual_idx = visible_start + i
        is_selected = actual_idx == selected_id
        marker = ">" if is_selected else " "
        active_status = "ACTIVE" if item.get("active", False) else "      "

        color = "green" if item.get("active", False) else "white"
        if is_selected:
            color = "cyan"

        item_displays.append(
            Text(
                f"{marker} [{actual_idx:04d}] {item['label']} | val:{item['value']:3d} | computed:{item['computed_value']:12.4f} | {active_status}",
                color=color,
            )
        )

    return Box(
        # Title bar
        Box(
            Text(" EXTREME STRESS TEST - WILL FREEZE IN SYNC MODE ", bold=True, reverse=True, color="red"),
            flexDirection="row",
        ),

        # Mode indicator
        Box(
            Text(f" Mode: {'CONCURRENT' if concurrent_mode else 'SYNC (will freeze!)'}", bold=True, color="green" if concurrent_mode else "red"),
            Text(f"  |  Items: {num_items}", color="cyan"),
            Text(f"  |  Multiplier: {multiplier}", color="magenta"),
            flexDirection="row",
        ),

        Box(marginTop=1),

        # Performance metrics
        Box(
            Text(" Performance: ", bold=True),
            Text(f"FPS: {fps:.1f} ({fps_status}) ", color=fps_color, bold=True),
            Text(f"  |  Pending: {'Yes' if is_pending else 'No'}", color="yellow" if is_pending else "green"),
            Text(f"  |  Selected: {selected_id}", color="cyan"),
            flexDirection="row",
        ),

        Box(marginTop=1),

        # Warning message
        Box(
            Text(
                " WARNING: This demo intentionally uses expensive computation to show freezing. " if not concurrent_mode
                else " Concurrent mode: Updates should feel smoother ",
                color="yellow" if not concurrent_mode else "green",
                bold=True,
            ),
            flexDirection="row",
        ),

        Box(marginTop=1),

        # List header
        Box(
            Text("   ID    Component      | Value | Computed     | Status", bold=True, underline=True),
            flexDirection="row",
        ),

        # Items
        Box(*item_displays, flexDirection="column"),

        Box(marginTop=1),

        # Controls
        Box(
            Text(" Controls: ↑↓ Navigate | Enter: Trigger Update | Ctrl+C: Exit", dimColor=True),
            flexDirection="row",
        ),

        Box(
            Text(f" Visible: {visible_start}-{visible_end} of {num_items} | Total computed items: {len(computed_items)}", dimColor=True),
            flexDirection="row",
        ),

        flexDirection="column",
    )


def main():
    parser = argparse.ArgumentParser(description="Extreme stress test - demonstrates UI freezing")
    parser.add_argument(
        "--items",
        type=int,
        default=1000,
        help="Number of items (default: 1000). Try 2000+ for extreme freeze!",
    )
    parser.add_argument(
        "--concurrent",
        action="store_true",
        help="Enable concurrent mode - should reduce freezing",
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print(" EXTREME STRESS TEST")
    print("=" * 60)
    print(f" Items: {args.items}")
    print(f" Mode: {'Concurrent' if args.concurrent else 'SYNC (warning: will freeze!)'}")
    print("\n This demo has INTENTIONALLY expensive computation (5ms/item)")
    print(f" Total compute time per frame: ~{args.items * 5}ms")
    print("\n In SYNC mode: UI will freeze for several seconds per update")
    print(" In CONCURRENT mode: Should be smoother, but still laggy")
    print("=" * 60 + "\n")

    def app():
        return ExtremeStressApp(
            num_items=args.items,
            concurrent_mode=args.concurrent,
        )

    render(app, concurrent=args.concurrent).wait_until_exit()


if __name__ == "__main__":
    main()
