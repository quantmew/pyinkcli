from __future__ import annotations

from contextlib import contextmanager

_ROUTER_CTX = {"stack": []}


def get_current_router():
    return _ROUTER_CTX["stack"][-1]


@contextmanager
def push_router_context(value):
    _ROUTER_CTX["stack"].append(value)
    try:
        yield
    finally:
        _ROUTER_CTX["stack"].pop()


__all__ = ["_ROUTER_CTX", "get_current_router", "push_router_context"]
