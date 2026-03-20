"""Translated subset of `react-router/lib/hooks.tsx`."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pyinkcli._component_runtime import RenderableNode, createElement, scopeRender
from pyinkcli.packages.react_router.context import (
    LocationContextObject,
    RouteContextObject,
    _get_location_context,
    _get_navigation_context,
    _get_outlet_context,
    _get_route_context,
    _provide_location_context,
    _provide_outlet_context,
    _provide_route_context,
)
from pyinkcli.packages.react_router.router.history import Action, parsePath
from pyinkcli.packages.react_router.router.utils import (
    RouteMatch,
    RouteObject,
    decodePath,
    getResolveToMatches,
    joinPaths,
    matchPath,
    matchRoutes,
    resolveTo,
)


def useInRouterContext() -> bool:
    return _get_location_context() is not None


def useLocation() -> Any:
    if not useInRouterContext():
        raise RuntimeError("useLocation() may be used only in the context of a <Router> component.")
    return _get_location_context().location


def useHref(to: Any, options: dict[str, Any] | None = None) -> str:
    if not useInRouterContext():
        raise RuntimeError("useHref() may be used only in the context of a <Router> component.")

    options = options or {}
    navigation_context = _get_navigation_context()
    resolved_path = useResolvedPath(to, options)
    pathname = resolved_path["pathname"]

    if navigation_context.basename != "/":
        pathname = (
            navigation_context.basename
            if pathname == "/"
            else joinPaths([navigation_context.basename, pathname])
        )

    return navigation_context.navigator.createHref(
        {
            "pathname": pathname,
            "search": resolved_path["search"],
            "hash": resolved_path["hash"],
        }
    )


def useNavigationType() -> str:
    if not useInRouterContext():
        raise RuntimeError("useNavigationType() may be used only in the context of a <Router> component.")
    return _get_location_context().navigationType


def useMatch(pattern: str | dict[str, Any]) -> dict[str, Any] | None:
    if not useInRouterContext():
        raise RuntimeError("useMatch() may be used only in the context of a <Router> component.")
    return matchPath(pattern, decodePath(useLocation().pathname))


def useNavigate() -> Callable[[Any, dict[str, Any] | None], None]:
    if not useInRouterContext():
        raise RuntimeError("useNavigate() may be used only in the context of a <Router> component.")

    navigation_context = _get_navigation_context()
    route_context = _get_route_context()
    location_pathname = useLocation().pathname
    route_pathnames = getResolveToMatches(route_context.matches)

    def navigate(to: Any, options: dict[str, Any] | None = None) -> None:
        options = options or {}
        if isinstance(to, int):
            navigation_context.navigator.go(to)
            return

        path = resolveTo(
            to,
            route_pathnames,
            location_pathname,
            options.get("relative") == "path",
        )

        if navigation_context.basename != "/":
            path["pathname"] = (
                navigation_context.basename
                if path["pathname"] == "/"
                else joinPaths([navigation_context.basename, path["pathname"]])
            )

        method = navigation_context.navigator.replace if options.get("replace") else navigation_context.navigator.push
        method(path, options.get("state"), options)

    return navigate


def useOutletContext() -> Any:
    return _get_outlet_context()


def useOutlet(context: Any = None) -> RenderableNode:
    outlet = _get_route_context().outlet
    if outlet is None:
        return None
    return scopeRender(outlet, lambda value=context: _provide_outlet_context(value))


def useParams() -> dict[str, str | None]:
    matches = _get_route_context().matches
    return matches[-1].params if matches else {}


def useResolvedPath(
    to: Any,
    options: dict[str, Any] | None = None,
) -> dict[str, str]:
    options = options or {}
    route_context = _get_route_context()
    location_pathname = useLocation().pathname
    route_pathnames = getResolveToMatches(route_context.matches)
    return resolveTo(
        to,
        route_pathnames,
        location_pathname,
        options.get("relative") == "path",
    )


def useRoutes(
    routes: list[RouteObject],
    locationArg: dict[str, Any] | str | None = None,
) -> RenderableNode:
    return useRoutesImpl(routes, locationArg)


def useRoutesImpl(
    routes: list[RouteObject],
    locationArg: dict[str, Any] | str | None = None,
) -> RenderableNode:
    if not useInRouterContext():
        raise RuntimeError("useRoutes() may be used only in the context of a <Router> component.")

    navigation_context = _get_navigation_context()
    parent_matches = _get_route_context().matches
    route_match = parent_matches[-1] if parent_matches else None
    parent_params = route_match.params if route_match else {}
    parent_pathname_base = route_match.pathnameBase if route_match else "/"

    location_from_context = useLocation()
    if locationArg is not None:
        parsed_location = parsePath(locationArg) if isinstance(locationArg, str) else locationArg
        if parent_pathname_base != "/" and not str(parsed_location.get("pathname", "")).startswith(parent_pathname_base):
            raise ValueError(
                "When overriding the location using `<Routes location>` or "
                "`useRoutes(routes, location)`, the location pathname must begin "
                "with the portion of the URL pathname matched by all parent routes."
            )
        location = parsed_location
    else:
        location = {
            "pathname": location_from_context.pathname,
            "search": location_from_context.search,
            "hash": location_from_context.hash,
            "state": getattr(location_from_context, "state", None),
            "key": getattr(location_from_context, "key", "default"),
            "unstable_mask": getattr(location_from_context, "unstable_mask", None),
        }

    pathname = location.get("pathname", "/") or "/"
    remaining_pathname = pathname
    if parent_pathname_base != "/":
        parent_segments = parent_pathname_base.lstrip("/").split("/")
        segments = pathname.lstrip("/").split("/")
        remaining_pathname = "/" + "/".join(segments[len(parent_segments):])

    matches = matchRoutes(routes, {"pathname": remaining_pathname})
    if matches is None:
        return None

    rendered_matches = [
        RouteMatch(
            params={**parent_params, **match.params},
            pathname=joinPaths([parent_pathname_base, navigation_context.navigator.encodeLocation(match.pathname).get("pathname", match.pathname)]),
            pathnameBase=(
                parent_pathname_base
                if match.pathnameBase == "/"
                else joinPaths(
                    [
                        parent_pathname_base,
                        navigation_context.navigator.encodeLocation(match.pathnameBase).get("pathname", match.pathnameBase),
                    ]
                )
            ),
            route=match.route,
        )
        for match in matches
    ]

    rendered = _renderMatches(rendered_matches, parent_matches)
    if locationArg is not None and rendered is not None:
        scoped_location = LocationContextObject(
            location=type(location_from_context)(
                pathname=location.get("pathname", "/"),
                search=location.get("search", ""),
                hash=location.get("hash", ""),
                state=location.get("state"),
                key=location.get("key", "default"),
                unstable_mask=location.get("unstable_mask"),
            ),
            navigationType=Action.Pop.value,
        )
        return scopeRender(rendered, lambda value=scoped_location: _provide_location_context(value))

    return rendered


def _renderMatches(
    matches: list[RouteMatch] | None,
    parentMatches: list[RouteMatch] | None = None,
) -> RenderableNode:
    if matches is None:
        return None

    parentMatches = [] if parentMatches is None else parentMatches
    outlet: RenderableNode = None
    rendered_matches = matches
    for index in range(len(rendered_matches) - 1, -1, -1):
        match = rendered_matches[index]
        route_matches = parentMatches + rendered_matches[: index + 1]

        if match.route.Component is not None:
            children = createElement(match.route.Component)
        elif match.route.element is not None:
            children = match.route.element
        else:
            children = outlet

        route_context = RouteContextObject(
            outlet=outlet,
            matches=route_matches,
            isDataRoute=False,
        )
        outlet = scopeRender(
            children,
            lambda value=route_context: _provide_route_context(value),
        )

    return outlet
