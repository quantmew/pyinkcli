"""Context objects translated from `react-router/lib/context.ts`."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Protocol


class Navigator(Protocol):
    def createHref(self, to: Any) -> str: ...
    def encodeLocation(self, to: Any) -> dict[str, str]: ...
    def go(self, delta: int) -> None: ...
    def push(self, to: Any, state: Any = None, opts: Any = None) -> None: ...
    def replace(self, to: Any, state: Any = None, opts: Any = None) -> None: ...


@dataclass
class NavigationContextObject:
    basename: str
    navigator: Navigator
    static: bool
    unstable_useTransitions: bool | None
    future: dict[str, Any]


@dataclass
class LocationContextObject:
    location: Any
    navigationType: str


@dataclass
class RouteContextObject:
    outlet: Any
    matches: list[Any]
    isDataRoute: bool


OutletContext: ContextVar[Any] = ContextVar(
    "react_router_outlet_context",
    default=None,
)


NavigationContext: ContextVar[NavigationContextObject | None] = ContextVar(
    "react_router_navigation_context",
    default=None,
)
LocationContext: ContextVar[LocationContextObject | None] = ContextVar(
    "react_router_location_context",
    default=None,
)
RouteContext: ContextVar[RouteContextObject | None] = ContextVar(
    "react_router_route_context",
    default=None,
)


def _get_navigation_context() -> NavigationContextObject | None:
    return NavigationContext.get()


def _get_location_context() -> LocationContextObject | None:
    return LocationContext.get()


def _get_route_context() -> RouteContextObject:
    context = RouteContext.get()
    return context or RouteContextObject(outlet=None, matches=[], isDataRoute=False)


def _get_outlet_context() -> Any:
    return OutletContext.get()


@contextmanager
def _provide_navigation_context(
    value: NavigationContextObject,
) -> Generator[None, None, None]:
    token = NavigationContext.set(value)
    try:
        yield
    finally:
        NavigationContext.reset(token)


@contextmanager
def _provide_location_context(
    value: LocationContextObject,
) -> Generator[None, None, None]:
    token = LocationContext.set(value)
    try:
        yield
    finally:
        LocationContext.reset(token)


@contextmanager
def _provide_route_context(value: RouteContextObject) -> Generator[None, None, None]:
    token = RouteContext.set(value)
    try:
        yield
    finally:
        RouteContext.reset(token)


@contextmanager
def _provide_outlet_context(value: Any) -> Generator[None, None, None]:
    token = OutletContext.set(value)
    try:
        yield
    finally:
        OutletContext.reset(token)
