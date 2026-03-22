"""Internal suspense resource runtime for pyinkcli."""

from __future__ import annotations

import threading
from collections.abc import Callable, Hashable
from dataclasses import dataclass, field
from typing import Any

from pyinkcli.packages.react.dispatcher import hasRerenderTarget, requestRerender
from pyinkcli.hooks import _runtime as hooks_runtime
from pyinkcli.packages.react_reconciler.ReactEventPriorities import (
    DefaultEventPriority,
    NoEventPriority,
    higherEventPriority,
)
from pyinkcli.packages.react_reconciler.ReactSharedInternals import shared_internals


class SuspendSignal(Exception):
    def __init__(self, key: Hashable):
        super().__init__(f"Suspended on resource {key!r}")
        self.key = key


@dataclass
class _ResourceRecord:
    status: str = "pending"
    value: Any = None
    error: Exception | None = None
    started: bool = False
    wake_priority: int = NoEventPriority
    lock: threading.Lock = field(default_factory=threading.Lock)


_records: dict[Hashable, _ResourceRecord] = {}
_records_lock = threading.Lock()
_resource_versions: dict[Hashable, int] = {}


def _record_resource_dependency(key: Hashable) -> None:
    try:
        fiber = hooks_runtime._get_current_fiber()
    except Exception:
        return

    versions = getattr(fiber, "suspense_resource_versions", None)
    if versions is None:
        versions = {}
        fiber.suspense_resource_versions = versions
    versions[key] = _resource_versions.get(key, 0)


def _resolve_resource(
    key: Hashable,
    record: _ResourceRecord,
    loader: Callable[[], Any],
) -> None:
    try:
        value = loader()
    except Exception as error:  # pragma: no cover
        with _records_lock:
            current = _records.get(key)
        if current is not record:
            return
        with record.lock:
            record.status = "rejected"
            record.error = error
    else:
        with _records_lock:
            current = _records.get(key)
        if current is not record:
            return
        with record.lock:
            record.status = "resolved"
            record.value = value

    if hasRerenderTarget():
        wake_priority = record.wake_priority or DefaultEventPriority
        requestRerender(priority=wake_priority)


def readResource(key: Hashable, loader: Callable[[], Any]) -> Any:
    _record_resource_dependency(key)
    with _records_lock:
        record = _records.get(key)
        if record is None:
            record = _ResourceRecord()
            _records[key] = record

    with record.lock:
        if record.status == "resolved":
            return record.value
        if record.status == "rejected":
            raise record.error  # type: ignore[misc]
        render_priority = (
            shared_internals.current_render_priority or DefaultEventPriority
        )
        record.wake_priority = higherEventPriority(record.wake_priority, render_priority)
        if not record.started:
            record.started = True
            threading.Thread(
                target=_resolve_resource,
                args=(key, record, loader),
                daemon=True,
            ).start()

    raise SuspendSignal(key)


def preloadResource(key: Hashable, loader: Callable[[], Any]) -> None:
    with _records_lock:
        record = _records.get(key)
        if record is None:
            record = _ResourceRecord()
            _records[key] = record

    with record.lock:
        if record.status in {"resolved", "rejected"} or record.started:
            return
        record.started = True
        threading.Thread(
            target=_resolve_resource,
            args=(key, record, loader),
            daemon=True,
        ).start()


def peekResource(key: Hashable) -> Any:
    with _records_lock:
        record = _records.get(key)
    if record is None:
        return None

    with record.lock:
        if record.status == "resolved":
            return record.value
        if record.status == "rejected":
            raise record.error  # type: ignore[misc]

    return None


def invalidateResource(key: Hashable) -> None:
    with _records_lock:
        _records.pop(key, None)
        _resource_versions[key] = _resource_versions.get(key, 0) + 1


def resetResource(key: Hashable) -> None:
    with _records_lock:
        _records.pop(key, None)
        _resource_versions[key] = _resource_versions.get(key, 0) + 1


def resetAllResources() -> None:
    with _records_lock:
        _records.clear()
        _resource_versions.clear()
