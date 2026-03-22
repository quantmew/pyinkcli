"""React.lazy compatibility helper."""

from __future__ import annotations

from typing import Any

from pyinkcli._component_runtime import renderComponent
from pyinkcli.packages.shared.ReactSymbols import REACT_LAZY_TYPE


def _resolve_default_export(module: Any) -> Any:
    if isinstance(module, dict):
        return module.get("default", module)
    default = getattr(module, "default", None)
    if default is not None:
        return default
    return module


def _lazy_initializer(payload: dict[str, Any]) -> Any:
    status = payload.get("_status", -1)
    if status == -1:
        loader = payload["_result"]
        module = loader()
        payload["_status"] = 1
        payload["_result"] = module
        return _resolve_default_export(module)
    if status == 1:
        return _resolve_default_export(payload["_result"])
    if status == 2:
        raise payload["_result"]
    return _resolve_default_export(payload["_result"])


class _LazyType:
    def __init__(self, loader) -> None:
        self.__dict__["$$typeof"] = REACT_LAZY_TYPE
        self._payload = {"_status": -1, "_result": loader}
        self._init = _lazy_initializer
        self._debugInfo = None
        self._store = {"validated": 0}
        self.displayName = None
        self.__ink_react_lazy__ = True

    def __call__(self, *children, **props):
        component = self._init(self._payload)
        return renderComponent(component, *children, **props)


def lazy(loader):
    return _LazyType(loader)


__all__ = ["lazy"]
