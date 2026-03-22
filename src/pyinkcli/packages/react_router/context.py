"""Shared router context and route object definitions."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

_NO_DEFAULT = object()


T = TypeVar("T")


@dataclass(frozen=True, eq=False)
class RouterContext(Generic[T]):
    defaultValue: Any = _NO_DEFAULT


def createContext(defaultValue: Any = _NO_DEFAULT) -> RouterContext:
    return RouterContext(defaultValue)


class RouterContextProvider:
    def __init__(self, init: dict[RouterContext, Any] | None = None):
        self._map: dict[RouterContext, Any] = {}
        if init:
            self._map.update(init)

    def get(self, context: RouterContext):
        if context in self._map:
            return self._map[context]
        if context.defaultValue is not _NO_DEFAULT:
            return context.defaultValue
        raise ValueError("No value found for context")

    def set(self, context: RouterContext, value: Any) -> None:
        self._map[context] = value


@dataclass
class RouteObject:
    caseSensitive: bool | None = None
    path: str | None = None
    id: str = ""
    middleware: Any = None
    loader: Any = None
    action: Any = None
    hasErrorBoundary: bool = False
    shouldRevalidate: Any = None
    handle: Any = None
    index: bool | None = None
    children: list["RouteObject"] | None = None
    element: Any = None
    hydrateFallbackElement: Any = None
    errorElement: Any = None
    Component: Any = None
    HydrateFallback: Any = None
    ErrorBoundary: Any = None
    lazy: Any = None


@dataclass
class RouteContextObject:
    outlet: Any = None
    matches: list[Any] = field(default_factory=list)
    isDataRoute: bool = False


@dataclass
class NavigationContextObject:
    basename: str
    navigator: Any
    static: bool
    unstable_useTransitions: bool | None
    future: dict[str, Any] = field(default_factory=dict)
    onError: Any = None


@dataclass
class LocationContextObject:
    location: Any
    navigationType: Any


@dataclass
class DataRouterContextObject:
    router: Any
    navigator: Any
    static: bool
    basename: str
    onError: Any = None


@dataclass
class ViewTransitionContextObject:
    isTransitioning: bool = False
    flushSync: bool = False
    currentLocation: Any = None
    nextLocation: Any = None


NavigationContextVar: ContextVar[NavigationContextObject | None] = ContextVar(
    "navigation_context",
    default=None,
)
LocationContextVar: ContextVar[LocationContextObject | None] = ContextVar(
    "location_context",
    default=None,
)
RouteContextVar: ContextVar[RouteContextObject] = ContextVar(
    "route_context",
    default=RouteContextObject(),
)
RouteErrorContextVar: ContextVar[Any] = ContextVar("route_error_context", default=None)
OutletContextVar: ContextVar[Any] = ContextVar("outlet_context", default=None)
DataRouterContextVar: ContextVar[DataRouterContextObject | None] = ContextVar(
    "data_router_context",
    default=None,
)
DataRouterStateContextVar: ContextVar[Any] = ContextVar(
    "data_router_state_context",
    default=None,
)
FetchersContextVar: ContextVar[Any] = ContextVar("fetchers_context", default=None)
ViewTransitionContextVar: ContextVar[ViewTransitionContextObject] = ContextVar(
    "view_transition_context",
    default=ViewTransitionContextObject(),
)


@contextmanager
def _provide_context(var: ContextVar, value: Any) -> Generator[None, None, None]:
    token = var.set(value)
    try:
        yield
    finally:
        var.reset(token)


def provide_navigation_context(value: NavigationContextObject):
    return _provide_context(NavigationContextVar, value)


def provide_location_context(value: LocationContextObject):
    return _provide_context(LocationContextVar, value)


def provide_route_context(value: RouteContextObject):
    return _provide_context(RouteContextVar, value)


def provide_route_error_context(value: Any):
    return _provide_context(RouteErrorContextVar, value)


def provide_outlet_context(value: Any):
    return _provide_context(OutletContextVar, value)


def provide_data_router_context(value: DataRouterContextObject):
    return _provide_context(DataRouterContextVar, value)


def provide_data_router_state(value: Any):
    return _provide_context(DataRouterStateContextVar, value)


def provide_fetchers_context(value: Any):
    return _provide_context(FetchersContextVar, value)


def provide_view_transition_context(value: ViewTransitionContextObject):
    return _provide_context(ViewTransitionContextVar, value)


__all__ = [
    "RouterContext",
    "RouterContextProvider",
    "RouteObject",
    "RouteContextObject",
    "NavigationContextObject",
    "LocationContextObject",
    "DataRouterContextObject",
    "ViewTransitionContextObject",
    "createContext",
    "NavigationContextVar",
    "LocationContextVar",
    "RouteContextVar",
    "RouteErrorContextVar",
    "OutletContextVar",
    "DataRouterContextVar",
    "DataRouterStateContextVar",
    "FetchersContextVar",
    "ViewTransitionContextVar",
    "provide_navigation_context",
    "provide_location_context",
    "provide_route_context",
    "provide_route_error_context",
    "provide_outlet_context",
    "provide_data_router_context",
    "provide_data_router_state",
    "provide_fetchers_context",
    "provide_view_transition_context",
]
