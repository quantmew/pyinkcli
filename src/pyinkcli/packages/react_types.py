from __future__ import annotations


class _MemoType:
    __ink_react_memo__ = True

    def __init__(self, type_):
        self.type = type_


def memo(type_):
    return _MemoType(type_)


class _ForwardRefType:
    __ink_react_forward_ref__ = True

    def __init__(self, render) -> None:
        self.render = render


def forwardRef(render):
    return _ForwardRefType(render)


class _LazyType:
    __ink_react_lazy__ = True

    def __init__(self, factory) -> None:
        self._factory = factory
        self._payload = None

    def _init(self, payload=None):
        if self._payload is None:
            self._payload = self._factory()
        return self._payload["default"]


def lazy(factory):
    return _LazyType(factory)


__all__ = ["forwardRef", "lazy", "memo"]
