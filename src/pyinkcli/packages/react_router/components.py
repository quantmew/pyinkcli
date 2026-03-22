"""Declarative router components."""

from __future__ import annotations

import re
from collections.abc import Iterable
from types import SimpleNamespace
from typing import Any

from pyinkcli._component_runtime import _Fragment, createElement, scopeRender

try:
    from pyinkcli.packages.react.dispatcher import requestRerender
except Exception:  # pragma: no cover - stripped-down fallback
    def requestRerender(*_args: Any, **_kwargs: Any) -> None:
        return None

from .context import (
    DataRouterContextObject,
    LocationContextObject,
    NavigationContextObject,
    RouteContextObject,
    RouteObject,
    ViewTransitionContextObject,
    provide_data_router_context,
    provide_data_router_state,
    provide_location_context,
    provide_navigation_context,
    provide_route_context,
    provide_view_transition_context,
)
from .router import (
    Action,
    Location,
    Path,
    RouteMatch,
    convertRoutesToDataRoutes,
    createMemoryHistory,
    matchRoutes,
    parsePath,
    stripBasename,
)

hydrationRouteProperties = ["HydrateFallback", "hydrateFallbackElement"]
_MEMORY_HISTORY_CACHE: dict[tuple[Any, ...], Any] = {}


def mapRouteProperties(route: RouteObject):
    updates: dict[str, Any] = {
        "hasErrorBoundary": bool(
            route.hasErrorBoundary or route.ErrorBoundary is not None or route.errorElement is not None
        )
    }
    if route.Component is not None:
        updates["element"] = createElement(route.Component)
        updates["Component"] = None
    if route.HydrateFallback is not None:
        updates["hydrateFallbackElement"] = createElement(route.HydrateFallback)
        updates["HydrateFallback"] = None
    if route.ErrorBoundary is not None:
        updates["errorElement"] = createElement(route.ErrorBoundary)
        updates["ErrorBoundary"] = None
    return updates


def _is_fragment(element: Any) -> bool:
    return getattr(element, "type", None) is _Fragment


def _iter_children(node: Any) -> Iterable[Any]:
    if node is None:
        return []
    if getattr(node, "type", None):
        return [node]
    if isinstance(node, (list, tuple)):
        return node
    if getattr(node, "children", None):
        return node.children
    props = getattr(node, "props", None) or {}
    children = props.get("children")
    if children is None:
        return []
    if isinstance(children, (list, tuple)):
        return children
    return [children]


def createRoutesFromChildren(children: Any, parentPath: list[int] | None = None) -> list[RouteObject]:
    parentPath = list(parentPath or [])
    routes: list[RouteObject] = []
    for index, element in enumerate(_iter_children(children)):
        if not getattr(element, "type", None):
            continue
        treePath = parentPath + [index]
        if _is_fragment(element):
            routes.extend(createRoutesFromChildren(getattr(element, "children", None), treePath))
            continue
        if element.type is not Route:
            raise ValueError(
                f"[{getattr(element.type, '__name__', element.type)}] is not a <Route> component. All component children of <Routes> must be a <Route> or <React.Fragment>"
            )
        props = getattr(element, "props", {}) or {}
        if props.get("index") and props.get("children") is not None:
            raise ValueError("An index route cannot have child routes.")
        route = RouteObject(
            id=props.get("id") or "-".join(str(item) for item in treePath),
            caseSensitive=props.get("caseSensitive"),
            element=props.get("element"),
            Component=props.get("Component"),
            index=props.get("index"),
            path=props.get("path"),
            middleware=props.get("middleware"),
            loader=props.get("loader"),
            action=props.get("action"),
            hydrateFallbackElement=props.get("hydrateFallbackElement"),
            HydrateFallback=props.get("HydrateFallback"),
            errorElement=props.get("errorElement"),
            ErrorBoundary=props.get("ErrorBoundary"),
            hasErrorBoundary=bool(
                props.get("hasErrorBoundary") is True
                or props.get("ErrorBoundary") is not None
                or props.get("errorElement") is not None
            ),
            shouldRevalidate=props.get("shouldRevalidate"),
            handle=props.get("handle"),
            lazy=props.get("lazy"),
        )
        if props.get("children") is not None:
            route.children = createRoutesFromChildren(props.get("children"), treePath)
        routes.append(route)
    return routes


createRoutesFromElements = createRoutesFromChildren


def Route(*_children: Any, **_props: Any):
    raise ValueError(
        "A <Route> is only ever to be used as the child of <Routes> element, never rendered directly. Please wrap your <Route> in a <Routes>."
    )


def _coalesce_children(children: tuple[Any, ...]) -> Any:
    if not children:
        return None
    if len(children) == 1:
        return children[0]
    return createElement(_Fragment, *children)


def Router(
    *children: Any,
    basename: str = "/",
    location: Any = None,
    navigationType: Action = Action.Pop,
    navigator: Any = None,
    static: bool = False,
    unstable_useTransitions: bool | None = None,
):
    if location is None:
        location = {"pathname": "/", "search": "", "hash": "", "state": None, "key": "default"}
    if isinstance(location, str):
        location = parsePath(location)
    if hasattr(location, "pathname"):
        pathname = location.pathname
        search = getattr(location, "search", "")
        hash_value = getattr(location, "hash", "")
        state = getattr(location, "state", None)
        key = getattr(location, "key", "default")
        unstable_mask = getattr(location, "unstable_mask", None)
    else:
        pathname = location.get("pathname", "/")
        search = location.get("search", "")
        hash_value = location.get("hash", "")
        state = location.get("state", None)
        key = location.get("key", "default")
        unstable_mask = location.get("unstable_mask")
    stripped = stripBasename(pathname, basename)
    if stripped is None:
        return None
    nav_context = NavigationContextObject(
        basename=re.sub(r"^/*", "/", basename),
        navigator=navigator,
        static=static,
        unstable_useTransitions=unstable_useTransitions,
        future={},
    )
    loc_context = LocationContextObject(
        location=Location(
            pathname=stripped,
            search=search,
            hash=hash_value,
            state=state,
            key=key,
            unstable_mask=unstable_mask,
        ),
        navigationType=navigationType,
    )
    body = _coalesce_children(children)
    return scopeRender(
        body,
        lambda: provide_navigation_context(nav_context),
        lambda: provide_location_context(loc_context),
    )


def MemoryRouter(
    *children: Any,
    basename: str = "/",
    initialEntries: list[str] | None = None,
    initialIndex: int | None = None,
    unstable_useTransitions: bool | None = None,
):
    cache_key = (
        basename,
        tuple(repr(item) for item in (initialEntries or ["/"])),
        initialIndex,
        unstable_useTransitions,
    )
    history = _MEMORY_HISTORY_CACHE.get(cache_key)
    if history is None:
        history = createMemoryHistory(
            {
                "initialEntries": initialEntries or ["/"],
                "initialIndex": initialIndex,
                "v5Compat": True,
            }
        )
        _MEMORY_HISTORY_CACHE[cache_key] = history
    history.listen(lambda _update: requestRerender())
    body = _coalesce_children(children)
    return Router(
        body,
        basename=basename,
        location=history.location,
        navigationType=history.action,
        navigator=history,
        unstable_useTransitions=unstable_useTransitions,
    )


def Navigate(
    *,
    to: str | Path,
    replace: bool | None = None,
    state: Any = None,
    relative: str | None = None,
):
    from .hooks import useNavigate

    navigate = useNavigate()
    navigate(to, {"replace": replace, "state": state, "relative": relative})
    return None


def Outlet(*, context: Any = None):
    from .hooks import useOutlet

    return useOutlet(context)


def Routes(*children: Any, location: Any = None):
    return useRoutes(createRoutesFromChildren(children), location)


def createMemoryRouter(routes: list[RouteObject], options: dict[str, Any] | None = None):
    options = dict(options or {})
    history = createMemoryHistory(
        {
            "initialEntries": options.get("initialEntries", ["/"]),
            "initialIndex": options.get("initialIndex"),
            "v5Compat": True,
        }
    )
    converted_routes = convertRoutesToDataRoutes(routes, mapRouteProperties)
    state = SimpleNamespace(
        location=history.location,
        historyAction=history.action,
        matches=matchRoutes(converted_routes, history.location, options.get("basename", "/")) or [],
        loaderData={},
        errors=None,
        navigation=SimpleNamespace(state="idle"),
        revalidation="idle",
        initialized=True,
        fetchers={},
    )
    subscribers: list[Any] = []

    def refresh_state() -> None:
        state.location = history.location
        state.historyAction = history.action
        state.matches = matchRoutes(converted_routes, history.location, options.get("basename", "/")) or []

    def notify(_update: Any) -> None:
        refresh_state()
        for subscriber in list(subscribers):
            subscriber()

    history.listen(notify)

    def subscribe(fn):
        subscribers.append(fn)

        def unsubscribe():
            if fn in subscribers:
                subscribers.remove(fn)

        return unsubscribe

    def navigate(to: Any, nav_options: dict[str, Any] | None = None):
        nav_options = nav_options or {}
        if isinstance(to, int):
            history.go(to)
            return
        if nav_options.get("replace"):
            history.replace(to, nav_options.get("state"))
        else:
            history.push(to, nav_options.get("state"))

    return SimpleNamespace(
        basename=options.get("basename", "/"),
        future=options.get("future", {}),
        routes=converted_routes,
        state=state,
        window=None,
        createHref=history.createHref,
        encodeLocation=history.encodeLocation,
        navigate=navigate,
        revalidate=lambda: None,
        subscribe=subscribe,
    )


def RouterProvider(*, router: Any, flushSync: bool | None = None):
    state = getattr(router, "state", None)
    if state is None:
        return None

    def go(delta: int) -> None:
        router.navigate(delta)

    def push(to: Any, _state: Any = None, _opts: dict[str, Any] | None = None) -> None:
        router.navigate(to, {"state": _state})

    def replace(to: Any, _state: Any = None, _opts: dict[str, Any] | None = None) -> None:
        router.navigate(to, {"state": _state, "replace": True})

    data_context = DataRouterContextObject(
        router=router,
        navigator=SimpleNamespace(
            createHref=router.createHref,
            encodeLocation=getattr(router, "encodeLocation", None),
            go=go,
            push=push,
            replace=replace,
        ),
        static=False,
        basename=getattr(router, "basename", "/"),
    )
    body = renderMatches(state.matches)
    return scopeRender(
        body,
        lambda: provide_data_router_context(data_context),
        lambda: provide_data_router_state(state),
        lambda: provide_view_transition_context(ViewTransitionContextObject(isTransitioning=False)),
    )


def renderMatches(matches: list[RouteMatch] | None):
    if matches is None:
        return None
    rendered: Any = None
    for index in range(len(matches) - 1, -1, -1):
        match = matches[index]
        outlet = rendered
        route_context = RouteContextObject(
            outlet=outlet,
            matches=matches[: index + 1],
            isDataRoute=False,
        )
        if match.route.Component is not None:
            children = createElement(match.route.Component)
        elif match.route.element is not None:
            children = match.route.element
        else:
            children = outlet
        rendered = scopeRender(
            children,
            lambda route_context=route_context: provide_route_context(route_context),
        )
    return rendered


def useRoutes(routes: list[RouteObject], location: Any = None):
    from .hooks import useRoutes as _useRoutes

    return _useRoutes(routes, location)


__all__ = [
    "hydrationRouteProperties",
    "mapRouteProperties",
    "createRoutesFromChildren",
    "createRoutesFromElements",
    "Route",
    "Router",
    "MemoryRouter",
    "Navigate",
    "Outlet",
    "Routes",
    "RouterProvider",
    "createMemoryRouter",
    "renderMatches",
]
