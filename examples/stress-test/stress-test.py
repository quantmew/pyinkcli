#!/usr/bin/env python3
"""
Stress test for pyinkcli - Performance test with many nodes.

This example demonstrates performance issues when updating a UI with
a large number of components. Use this to test and profile rendering
performance under heavy load.

Run with:
    python stress-test.py                    # Default: 500 items
    python stress-test.py --items 1000       # 1000 items
    python stress-test.py --items 2000 --concurrent  # 2000 items with concurrent mode
"""

from __future__ import annotations

import argparse
import random
import threading
import time
from typing import Any

from pyinkcli import Box, Text, render, useInput
from pyinkcli.hooks import useEffect, useMemo, useState, useTransition


# Colors for list items
ITEM_COLORS = ["red", "green", "yellow", "blue", "magenta", "cyan", "white"]


def _generate_large_list(count: int, seed: int = 0) -> list[dict[str, Any]]:
    """Generate a large list of items with various properties."""
    random.seed(seed)
    items = []
    for i in range(count):
        items.append({
            "id": i,
            "name": f"Item {i + 1}",
            "value": random.randint(0, 1000),
            "status": random.choice(["active", "pending", "completed", "error"]),
            "progress": random.randint(0, 100),
            "color": random.choice(ITEM_COLORS),
            "timestamp": time.time() - random.randint(0, 3600),
        })
    return items


def _compute_intensive(items: list[dict[str, Any]], multiplier: int) -> list[dict[str, Any]]:
    """Simulate expensive computation during render."""
    result = []
    for item in items:
        # Simulate expensive computation
        computed_value = item["value"] * multiplier
        for _ in range(100):
            computed_value = (computed_value * 1.001) % 1000

        result.append({
            **item,
            "computed": round(computed_value, 2),
            "formatted_value": f"{computed_value:.2f}",
        })
    return result


def StatusBar(
    total_items: int,
    updating_items: int,
    fps: float,
    render_time_ms: float,
    is_pending: bool,
    concurrent_mode: bool,
) -> Box:
    """Render a status bar with performance metrics."""
    status_color = "yellow" if is_pending else "green"
    mode_text = "Concurrent" if concurrent_mode else "Sync"

    return Box(
        Text(" [", dimColor=True),
        Text(f" {mode_text} Mode ", bold=True),
        Text("] ", dimColor=True),
        Text(f"Items: {total_items}", color="cyan"),
        Text(" | "),
        Text(f"Updating: {updating_items}", color=status_color),
        Text(" | "),
        Text(f"FPS: {fps:.1f}", color="green" if fps > 30 else "yellow" if fps > 10 else "red"),
        Text(" | "),
        Text(f"Render: {render_time_ms:.1f}ms", color="green" if render_time_ms < 50 else "yellow" if render_time_ms < 200 else "red"),
        flexDirection="row",
    )


def ListItem(
    item: dict[str, Any],
    index: int,
    is_highlighted: bool = False,
) -> Text:
    """Render a single list item."""
    status_icons = {
        "active": "[+]",
        "pending": "[~]",
        "completed": "[✓]",
        "error": "[!]",
    }
    icon = status_icons.get(item["status"], "[?]")

    # Color based on status
    status_colors = {
        "active": "green",
        "pending": "yellow",
        "completed": "cyan",
        "error": "red",
    }

    highlight = " <- " if is_highlighted else ""

    return Text(
        f"  {icon} {item['name']:>6} | Value: {item['value']:>4} | Computed: {item['formatted_value']:>10} | Progress: {item['progress']:>3}%{highlight}",
        color=status_colors.get(item["status"], "white"),
        dimColor=item["status"] == "completed",
    )


def StressTestApp(num_items: int, update_interval: float, concurrent_mode: bool):
    """Main stress test application."""

    # State
    items, set_items = useState(lambda: _generate_large_list(num_items, seed=42))
    multiplier, set_multiplier = useState(1)
    selected_index, set_selected_index = useState(0)
    is_running, set_is_running = useState(True)

    # Transition for concurrent updates
    is_pending, start_transition = useTransition()

    # Performance metrics
    fps_ref, set_fps_ref = useState({"fps": 0.0, "render_time": 0.0, "last_update": time.time()})
    frame_count_ref = {"count": 0, "start_time": time.time()}

    # Track render times
    render_start_ref = {"time": 0}

    def update_frame_metrics():
        """Update FPS and render time metrics."""
        now = time.time()
        frame_count_ref["count"] += 1

        # Calculate FPS every second
        elapsed = now - frame_count_ref["start_time"]
        if elapsed >= 1.0:
            fps = frame_count_ref["count"] / elapsed
            frame_count_ref["count"] = 0
            frame_count_ref["start_time"] = now

            render_time = now - render_start_ref["time"] if render_start_ref["time"] > 0 else 0
            set_fps_ref({
                "fps": fps,
                "render_time": render_time * 1000,  # Convert to ms
                "last_update": now,
            })

    # Auto-update items periodically
    def setup_auto_update():
        if not is_running:
            return None

        running = True

        def auto_update():
            nonlocal running
            while running and is_running:
                time.sleep(update_interval)

                # Update random subset of items
                def update_items(current_items):
                    new_items = current_items.copy()
                    num_updates = max(1, num_items // 10)  # Update 10% of items

                    for _ in range(num_updates):
                        idx = random.randint(0, len(new_items) - 1)
                        item = new_items[idx].copy()
                        item["value"] = random.randint(0, 1000)
                        item["progress"] = random.randint(0, 100)
                        item["timestamp"] = time.time()
                        new_items[idx] = item

                    # Increment multiplier to trigger re-computation
                    start_transition(lambda: set_multiplier(lambda m: (m % 10) + 1))
                    return new_items

                set_items(update_items)

        thread = threading.Thread(target=auto_update, daemon=True)
        thread.start()

        def cleanup():
            running = False

        return cleanup

    useEffect(setup_auto_update, [is_running, update_interval])

    # Keyboard controls
    def handle_input(input_char, key) -> None:
        nonlocal num_items

        if key.ctrl:
            if input_char == "c":
                return  # Let Ctrl+C pass through
            if input_char == "r":
                # Reset items
                set_items(_generate_large_list(num_items, seed=random.randint(0, 10000)))
                return
            if input_char == "t":
                # Toggle running state
                set_is_running(not is_running)
                return

        # Arrow keys for navigation
        if key.up_arrow:
            set_selected_index(max(0, selected_index - 1))
        elif key.down_arrow:
            set_selected_index(min(len(items) - 1, selected_index + 1))
        elif key.page_up:
            set_selected_index(max(0, selected_index - 20))
        elif key.page_down:
            set_selected_index(min(len(items) - 1, selected_index + 20))
        elif key.home:
            set_selected_index(0)
        elif key.end:
            set_selected_index(len(items) - 1)

    useInput(handle_input)

    # Expensive computation (simulates real-world heavy computation)
    computed_items = useMemo(
        lambda: _compute_intensive(items, multiplier),
        (items, multiplier),
    )

    # Update render metrics
    update_frame_metrics()

    # Build visible items (limit to avoid terminal overflow)
    max_visible = 30  # Show max 30 items on screen
    visible_start = max(0, min(selected_index - max_visible // 2, len(computed_items) - max_visible))
    visible_items = computed_items[visible_start:visible_start + max_visible]

    # Render list items
    list_item_elements = [
        ListItem(item, i, is_highlighted=(visible_start + i) == selected_index)
        for i, item in enumerate(visible_items)
    ]

    # Build help text
    help_text = (
        "Controls: ↑↓ Navigate | PgUp/PgDn Scroll | R: Reset | T: Toggle Updates | Ctrl+C: Exit"
    )

    # Count items by status
    status_counts = {}
    for item in items:
        status = item["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    status_summary = " | ".join([
        f"{status}: {count}"
        for status, count in sorted(status_counts.items())
    ])

    return Box(
        # Header
        Box(
            Text(" Stress Test - Large List Performance ", bold=True, reverse=True),
            flexDirection="row",
        ),

        # Stats
        Box(
            Text(f"  Total Items: {num_items}  |  ", dimColor=True),
            Text(f"Multipler: {multiplier}", color="magenta"),
            Text("  |  ", dimColor=True),
            Text(status_summary, dimColor=True),
            flexDirection="row",
        ),

        # Status bar with metrics
        StatusBar(
            total_items=num_items,
            updating_items=num_items // 10,
            fps=fps_ref["fps"],
            render_time_ms=fps_ref["render_time"],
            is_pending=is_pending,
            concurrent_mode=concurrent_mode,
        ),

        # Scroll indicator
        Box(
            Text(
                f"  Showing {visible_start + 1}-{min(visible_start + len(visible_items), len(items))} of {len(items)} (selected: {selected_index + 1})",
                dimColor=True,
            ),
            flexDirection="row",
        ),

        Box(marginTop=1),

        # Item list header
        Box(
            Text("  Icon Name    | Value | Computed   | Progress", bold=True, underline=True),
            flexDirection="row",
        ),

        # Items list
        Box(
            *list_item_elements,
            flexDirection="column",
        ),

        Box(marginTop=1),

        # Help
        Box(
            Text(f"  {help_text}", dimColor=True),
            flexDirection="row",
        ),

        Box(marginTop=1),

        # Running status
        Box(
            Text(
                f"  Status: {'Running (auto-updating)' if is_running else 'Paused'}  |  "
                f"Updates every {update_interval}s  |  "
                f"Press 'T' to {'pause' if is_running else 'resume'}",
                color="green" if is_running else "yellow",
            ),
            flexDirection="row",
        ),

        flexDirection="column",
    )


def main():
    parser = argparse.ArgumentParser(description="Stress test for pyinkcli with many nodes")
    parser.add_argument(
        "--items",
        type=int,
        default=500,
        help="Number of items to render (default: 500)",
    )
    parser.add_argument(
        "--update-interval",
        type=float,
        default=1.0,
        help="Interval between automatic updates in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--concurrent",
        action="store_true",
        help="Enable concurrent mode for smoother updates",
    )

    args = parser.parse_args()

    print(f"\nStarting stress test with {args.items} items...")
    print(f"Update interval: {args.update_interval}s")
    print(f"Concurrent mode: {args.concurrent}")
    print("\n")

    def app():
        return StressTestApp(
            num_items=args.items,
            update_interval=args.update_interval,
            concurrent_mode=args.concurrent,
        )

    render(app, concurrent=args.concurrent).wait_until_exit()


if __name__ == "__main__":
    main()
