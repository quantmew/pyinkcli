from __future__ import annotations

import threading

DefaultEventPriority = 4


class SuspendSignal(Exception):
    pass


_resources: dict[str, dict] = {}
_renderer_rerender = None
_records: dict[str, object] = {}


def _entry(key: str) -> dict:
    return _resources.setdefault(
        key,
        {"status": "empty", "value": None, "error": None, "thread": None},
    )


def _set_renderer_rerender(callback) -> None:
    global _renderer_rerender
    _renderer_rerender = callback


def readResource(key: str, loader):
    entry = _entry(key)
    if entry["status"] == "resolved":
        return entry["value"]
    if entry["status"] == "rejected":
        raise entry["error"]
    if entry["status"] == "pending":
        raise SuspendSignal(key)

    entry["status"] = "pending"
    _records[key] = type("SuspenseRecord", (), {"wake_priority": DefaultEventPriority})()

    def run() -> None:
        try:
            entry["value"] = loader()
            entry["status"] = "resolved"
        except Exception as error:  # noqa: BLE001
            entry["error"] = error
            entry["status"] = "rejected"
        callback = _renderer_rerender
        owner = getattr(callback, "__self__", None)
        if owner is not None and getattr(owner, "_is_unmounted", False):
            from .hooks import _runtime as hooks_runtime

            hooks_runtime._pending_rerender_priority = None
            return
        if callable(callback):
            callback()
            return
        from .hooks import _runtime as hooks_runtime

        hooks_runtime._pending_rerender_priority = None

    thread = threading.Thread(target=run, daemon=True)
    entry["thread"] = thread
    thread.start()
    raise SuspendSignal(key)


def preloadResource(key: str, loader):
    try:
        return readResource(key, loader)
    except SuspendSignal:
        return None


def peekResource(key: str):
    entry = _resources.get(key)
    if not entry or entry["status"] != "resolved":
        return None
    return entry["value"]


def invalidateResource(key: str) -> None:
    _resources.pop(key, None)


def resetResource(key: str) -> None:
    invalidateResource(key)


def resetAllResources() -> None:
    _resources.clear()


__all__ = [
    "SuspendSignal",
    "readResource",
    "preloadResource",
    "peekResource",
    "invalidateResource",
    "resetResource",
    "resetAllResources",
]
