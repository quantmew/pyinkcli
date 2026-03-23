from __future__ import annotations

from typing import Callable

_instances: dict[int, object] = {}


def _stream_key(stream) -> int:
    return id(stream)


def get(stream):
    return _instances.get(_stream_key(stream))


def has(stream) -> bool:
    return _stream_key(stream) in _instances


def set(stream, instance) -> None:
    _instances[_stream_key(stream)] = instance


def get_instance(stream, factory: Callable[[], object]):
    key = _stream_key(stream)
    instance = _instances.get(key)
    if instance is None or getattr(instance, "_is_unmounted", False):
        instance = factory()
        _instances[key] = instance
    return instance


def delete_instance(stream) -> None:
    _instances.pop(_stream_key(stream), None)


def cleanup() -> None:
    for instance in list(_instances.values()):
        try:
            instance.unmount()
        except Exception:  # noqa: BLE001
            pass
    _instances.clear()


__all__ = ["cleanup", "delete_instance", "get", "get_instance", "has", "set"]
