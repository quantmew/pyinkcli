"""Translated subset of `react-router/lib/components.tsx`."""

from __future__ import annotations

from typing import Any, Optional

from pyinkcli._component_runtime import RenderableNode, _Fragment, createElement, isElement, scopeRender
from pyinkcli.hooks import useEffect, useRef, useState
from pyinkcli.packages.react_router.context import (
    LocationContextObject,
    NavigationContextObject,
    _get_route_context,
    _provide_location_context,
    _provide_navigation_context,
)
from pyinkcli.packages.react_router.hooks import useInRouterContext, useLocation, useNavigate, useOutlet, useRoutes
from pyinkcli.packages.react_router.router.history import Action, Location, MemoryHistory, createMemoryHistory, parsePath
from pyinkcli.packages.react_router.router.utils import RouteObject, getResolveToMatches, resolveTo, stripBasename


def mapRouteProperties(route: RouteObject) -> dict[str, Any]:
    updates: dict[str, Any] = {
        "hasErrorBoundary": (
            route.hasErrorBoundary
            or route.ErrorBoundary is not None
            or route.errorElement is not None
        ),
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


hydrationRouteProperties = [
    "HydrateFallback",
    "hydrateFallbackElement",
]


def MemoryRouter(
    *children: RenderableNode,
    basename: Optional[str] = None,
    initialEntries: Optional[list[str | dict[str, Any]]] = None,
    initialIndex: Optional[int] = None,
    unstable_useTransitions: Optional[bool] = None,
) -> RenderableNode:
    historyRef = useRef(None)
    if historyRef.current is None:
        historyRef.current = createMemoryHistory(
            {
                "initialEntries": initialEntries,
                "initialIndex": initialIndex,
                "v5Compat": True,
            }
        )

    history: MemoryHistory = historyRef.current
    state, setStateImpl = useState(
        lambda: {
            "action": history.action.value if hasattr(history.action, "value") else history.action,
            "location": history.location,
        }
    )

    def setState(newState: dict[str, Any]) -> None:
        setStateImpl(newState)

    def subscribe() -> Any:
        return history.listen(
            lambda update: setState(
                {
                    "action": update.action.value if hasattr(update.action, "value") else update.action,
                    "location": update.location,
                }
            )
        )

    useEffect(subscribe, (history,))

    return createElement(
        Router,
        *children,
        basename=basename or "/",
        location=state["location"],
        navigationType=state["action"],
        navigator=history,
        unstable_useTransitions=unstable_useTransitions,
    )


def Route(**props: Any) -> RenderableNode:
    raise RuntimeError(
        "A <Route> is only ever to be used as the child of <Routes> element, "
        "never rendered directly. Please wrap your <Route> in a <Routes>."
    )


def Navigate(
    to: Any,
    replace: Optional[bool] = None,
    state: Any = None,
    relative: Optional[str] = None,
) -> RenderableNode:
    if not useInRouterContext():
        raise RuntimeError("<Navigate> may be used only in the context of a <Router> component.")

    matches = _get_route_context().matches
    location_pathname = useLocation().pathname
    navigate = useNavigate()
    path = resolveTo(
        to,
        getResolveToMatches(matches),
        location_pathname,
        relative == "path",
    )

    def perform_navigation() -> None:
        navigate(
            path,
            {
                "replace": replace,
                "state": state,
                "relative": relative,
            },
        )

    useEffect(perform_navigation, (str(path), replace, state, relative))
    return None


def Router(
    *children: RenderableNode,
    basename: str = "/",
    location: dict[str, Any] | str | Location = "/",
    navigationType: str = Action.Pop.value,
    navigator: Any = None,
    static: bool = False,
    unstable_useTransitions: Optional[bool] = None,
) -> RenderableNode:
    if useInRouterContext():
        raise RuntimeError("You cannot render a <Router> inside another <Router>.")

    basename_value = "/" + basename.lstrip("/")
    navigation_context = NavigationContextObject(
        basename=basename_value,
        navigator=navigator,
        static=static,
        unstable_useTransitions=unstable_useTransitions,
        future={},
    )

    location_prop = parsePath(location) if isinstance(location, str) else (
        {
            "pathname": location.pathname,
            "search": location.search,
            "hash": location.hash,
            "state": location.state,
            "key": location.key,
            "unstable_mask": location.unstable_mask,
        }
        if isinstance(location, Location)
        else dict(location)
    )

    pathname = location_prop.get("pathname", "/")
    search = location_prop.get("search", "")
    hash_value = location_prop.get("hash", "")
    state = location_prop.get("state")
    key = location_prop.get("key", "default")
    unstable_mask = location_prop.get("unstable_mask")

    trailing_pathname = stripBasename(pathname, basename_value)
    if trailing_pathname is None:
        return None

    location_context = LocationContextObject(
        location=Location(
            pathname=trailing_pathname,
            search=search,
            hash=hash_value,
            state=state,
            key=key,
            unstable_mask=unstable_mask,
        ),
        navigationType=navigationType,
    )

    body: RenderableNode
    if len(children) == 0:
        body = None
    elif len(children) == 1:
        body = children[0]
    else:
        body = createElement(_Fragment, *children)

    return scopeRender(
        body,
        lambda value=navigation_context: _provide_navigation_context(value),
        lambda value=location_context: _provide_location_context(value),
    )


def Routes(
    *route_children: RenderableNode,
    children: Any = None,
    location: Optional[dict[str, Any] | str] = None,
) -> RenderableNode:
    resolved_children = _coalesce_route_children(route_children, children)
    return useRoutes(createRoutesFromChildren(resolved_children), location)


def Outlet(context: Any = None) -> RenderableNode:
    return useOutlet(context)


def createRoutesFromChildren(
    children: Any,
    parentPath: Optional[list[int]] = None,
) -> list[RouteObject]:
    parentPath = [] if parentPath is None else parentPath
    routes: list[RouteObject] = []

    for index, element in enumerate(_iter_route_children(children)):
        if not isElement(element):
            continue

        treePath = [*parentPath, index]

        if getattr(element, "type", None) is _Fragment:
            routes.extend(createRoutesFromChildren(getattr(element, "children", []), treePath))
            continue

        invariant_message = (
            f"[{getattr(getattr(element, 'type', None), '__name__', getattr(element, 'type', None))}] "
            "is not a <Route> component. All component children of <Routes> must "
            "be a <Route> or <React.Fragment>"
        )
        if getattr(element, "type", None) is not Route:
            raise ValueError(invariant_message)

        props = dict(getattr(element, "props", {}))
        route_children = props.get("children", getattr(element, "children", []))
        if props.get("index") and route_children:
            raise ValueError("An index route cannot have child routes.")

        route = RouteObject(
            id=str(props.get("id", "-".join(str(part) for part in treePath))),
            caseSensitive=props.get("caseSensitive", False) is True,
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
            hasErrorBoundary=(
                props.get("hasErrorBoundary") is True
                or props.get("ErrorBoundary") is not None
                or props.get("errorElement") is not None
            ),
            shouldRevalidate=props.get("shouldRevalidate"),
            handle=props.get("handle"),
            lazy=props.get("lazy"),
        )

        if route_children:
            route.children = createRoutesFromChildren(route_children, treePath)

        routes.append(route)

    return routes


def createRoutesFromElements(
    children: Any,
    parentPath: Optional[list[int]] = None,
) -> list[RouteObject]:
    return createRoutesFromChildren(children, parentPath)


def _iter_route_children(children: Any) -> list[Any]:
    if children is None:
        return []
    if isinstance(children, (list, tuple)):
        result: list[Any] = []
        for child in children:
            result.extend(_iter_route_children(child))
        return result
    return [children]


def _coalesce_route_children(
    route_children: tuple[RenderableNode, ...],
    children: Any,
) -> Any:
    if not route_children:
        return children
    if children is None:
        if len(route_children) == 1:
            return route_children[0]
        return list(route_children)
    return [*route_children, children]
