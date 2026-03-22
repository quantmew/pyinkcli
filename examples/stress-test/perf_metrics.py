"""Shared performance metric collection for stress-test examples."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any


class PerfMetricCollector:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._frames = 0
            self._window_start = time.time()
            self._fps = 0.0
            self._render_time_ms = 0.0

    def record_render(self, metrics: Any) -> None:
        now = time.time()
        with self._lock:
            self._frames += 1
            self._render_time_ms = getattr(metrics, "render_time", 0.0) * 1000
            elapsed = now - self._window_start
            if elapsed > 0:
                self._fps = self._frames / elapsed
            if elapsed >= 1.0:
                self._frames = 0
                self._window_start = now

    def snapshot(self) -> dict[str, float]:
        with self._lock:
            return {
                "fps": self._fps,
                "render_time_ms": self._render_time_ms,
            }


def use_perf_metrics(useEffect, useState, collector: PerfMetricCollector):
    metrics, set_metrics = useState({"fps": 0.0, "render_time_ms": 0.0})

    def setup_metrics_sync():
        running = True

        def run():
            while running:
                set_metrics(collector.snapshot())
                time.sleep(0.25)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

        def cleanup():
            nonlocal running
            running = False

        return cleanup

    useEffect(setup_metrics_sync, ())
    return metrics

