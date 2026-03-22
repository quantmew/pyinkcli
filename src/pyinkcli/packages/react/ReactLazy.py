"""Lazy component helpers aligned with ReactLazy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

Uninitialized = -1
Pending = 0
Resolved = 1
Rejected = 2


@dataclass
class _LazyPayload:
    _status: int
    _result: Any


@dataclass
class ReactLazyType:
    _payload: _LazyPayload
    _init: Any
    __ink_devtools_react_lazy__: bool = True
    __ink_react_lazy__: bool = True


def lazyInitializer(payload: _LazyPayload) -> Any:
    if payload._status == Uninitialized:
        try:
            module_object = payload._result()
            payload._status = Resolved
            payload._result = module_object
        except BaseException as error:
            payload._status = Rejected
            payload._result = error
            raise
    if payload._status == Resolved:
        module_object = payload._result
        if isinstance(module_object, dict) and "default" in module_object:
            return module_object["default"]
        default = getattr(module_object, "default", None)
        return module_object if default is None else default
    raise payload._result


def lazy(load):
    payload = _LazyPayload(_status=Uninitialized, _result=load)
    return ReactLazyType(_payload=payload, _init=lazyInitializer)


__all__ = [
    "Pending",
    "ReactLazyType",
    "Rejected",
    "Resolved",
    "Uninitialized",
    "lazy",
    "lazyInitializer",
]
