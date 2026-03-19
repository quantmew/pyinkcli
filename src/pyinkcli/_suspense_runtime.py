"""Internal suspense resource runtime for pyinkcli."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Hashable

from pyinkcli.hooks._runtime import _has_rerender_target, _request_rerender


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
    lock: threading.Lock = field(default_factory=threading.Lock)


_records: dict[Hashable, _ResourceRecord] = {}
_records_lock = threading.Lock()


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

    if _has_rerender_target():
        _request_rerender()


def readResource(key: Hashable, loader: Callable[[], Any]) -> Any:
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


def resetResource(key: Hashable) -> None:
    with _records_lock:
        _records.pop(key, None)


def resetAllResources() -> None:
    with _records_lock:
        _records.clear()
