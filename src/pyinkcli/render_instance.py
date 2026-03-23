from __future__ import annotations

import sys

from . import instances

_REUSE_STDOUT_WARNING = (
    "Warning: render() was called again for the same stdout before the previous Ink instance "
    "was unmounted. Reusing stdout across multiple render() calls is unsupported. Call "
    "unmount() first.\n"
)


def get_instance(stream, factory, *, warning_stream=None):
    instance = instances.get(stream)
    if instance is None or getattr(instance, "_is_unmounted", False):
        instance = factory()
        instances.set(stream, instance)
        return instance

    target_stream = warning_stream or sys.stderr
    write = getattr(target_stream, "write", None)
    if callable(write):
        write(_REUSE_STDOUT_WARNING)
    return instance


__all__ = ["get_instance"]
