"""Router hooks implemented against the local context runtime."""

from __future__ import annotations

from typing import Any

from .context import (
    DataRouterContextVar,
    DataRouterStateContextVar,
    LocationContextObject,
    LocationContextVar,
    NavigationContextVar,
    OutletContextVar,
    RouteContextVar,
    RouteErrorContextVar,
)
from .router import (
    UIMatch,
    convertRouteMatchToUiMatch,
    decodePath,
    getResolveToMatches,
    getRoutePattern,
    isBrowser,
    isRouteErrorResponse,
    joinPaths,
    matchPath,
    matchRoutes,
    parsePath,
    resolveTo,
    stripBasename,
    Path,
)


def useInRouterContext() -> bool:
    return LocationContextVar.get() is not None


def _require_router(hook: str) -> None:
    if not useInRouterContext():
        raise ValueError(f"{hook} may be used only in the context of a <Router> component.")


def useLocation():
    _require_router("useLocation()")
    return LocationContextVar.get().location


def useNavigationType():
    _require_router("useNavigationType()")
    navigation_type = LocationContextVar.get().navigationType
    return getattr(navigation_type, "value", navigation_type)


def useHref(to: Any, options: dict[str, Any] | None = None) -> str:
    _require_router("useHref()")
    options = options or {}
    basename = NavigationContextVar.get().basename if NavigationContextVar.get() else "/"
    navigator = NavigationContextVar.get().navigator
    path = useResolvedPath(to, {"relative": options.get("relative")})
    pathname = path.pathname
    if basename != "/":
        pathname = basename if pathname == "/" else joinPaths([basename, pathname])
    return navigator.createHref({"pathname": pathname, "search": path.search, "hash": path.hash})


def useNavigate():
    _require_router("useNavigate()")
    navigation_context = NavigationContextVar.get()
    basename = navigation_context.basename if navigation_context else "/"
    navigator = navigation_context.navigator if navigation_context else None
    route_pathnames = getResolveToMatches(RouteContextVar.get().matches)
    location_pathname = useLocation().pathname

    def navigate(to: Any, options: dict[str, Any] | None = None):
        opts = options or {}
        if isinstance(to, int):
            navigator.go(to)
            return
        path = resolveTo(to, route_pathnames, location_pathname, opts.get("relative") == "path")
        if basename != "/":
            path = Path(
                pathname=basename if path.pathname == "/" else joinPaths([basename, path.pathname]),
                search=path.search,
                hash=path.hash,
            )
        action = navigator.replace if opts.get("replace") else navigator.push
        action(path, opts.get("state"))

    return navigate


def useMatch(pattern: Any):
    _require_router("useMatch()")
    pathname = decodePath(useLocation().pathname)
    return matchPath(pattern, pathname)


def useResolvedPath(to: Any, options: dict[str, Any] | None = None):
    _require_router("useResolvedPath()")
    options = options or {}
    matches = RouteContextVar.get().matches
    locationPathname = useLocation().pathname
    return resolveTo(to, getResolveToMatches(matches), locationPathname, options.get("relative") == "path")


def useOutletContext():
    return OutletContextVar.get()


def useOutlet(context: Any = None):
    outlet = RouteContextVar.get().outlet
    if outlet is None:
        return None
    from pyinkcli._component_runtime import scopeRender

    from .context import provide_outlet_context

    return scopeRender(outlet, lambda: provide_outlet_context(context))


def useParams():
    matches = RouteContextVar.get().matches
    if not matches:
        return {}
    return matches[-1].params


def useRoutes(routes, locationArg=None):
    _require_router("useRoutes()")
    location_from_context = useLocation()
    location = parsePath(locationArg) if isinstance(locationArg, str) else locationArg
    location = location or location_from_context
    pathname = location.get("pathname", "/") if isinstance(location, dict) else getattr(location, "pathname", "/")
    matches = matchRoutes(routes, {"pathname": pathname})
    if matches is None:
        return None
    from pyinkcli._component_runtime import scopeRender
    from .context import provide_location_context

    from .components import renderMatches

    rendered = renderMatches(matches)
    if locationArg and rendered is not None:
        return scopeRender(
            rendered,
            lambda: provide_location_context(
                LocationContextObject(location=location, navigationType=useNavigationType())
            ),
        )
    return rendered


def useNavigation():
    state = DataRouterStateContextVar.get()
    if state is None:
        return type("Navigation", (), {"state": "idle"})()
    return state.navigation


def useRevalidator():
    state = DataRouterStateContextVar.get()
    if state is None:
        return {"revalidate": lambda: None, "state": "idle"}
    router = DataRouterContextVar.get().router
    return {"revalidate": getattr(router, "revalidate", lambda: None), "state": state.revalidation}


def useMatches():
    state = DataRouterStateContextVar.get()
    if state is None:
        return []
    loaderData = getattr(state, "loaderData", {})
    return [convertRouteMatchToUiMatch(match, loaderData) for match in state.matches]


def useLoaderData():
    state = DataRouterStateContextVar.get()
    route = RouteContextVar.get().matches[-1] if RouteContextVar.get().matches else None
    if state is None or route is None:
        return None
    return getattr(state, "loaderData", {}).get(route.route.id)


def useRouteLoaderData(routeId: str):
    state = DataRouterStateContextVar.get()
    if state is None:
        return None
    return getattr(state, "loaderData", {}).get(routeId)


def useActionData():
    state = DataRouterStateContextVar.get()
    if state is None:
        return None
    return getattr(state, "actionData", None)


def useRouteError():
    error = RouteErrorContextVar.get()
    if error is not None:
        return error
    state = DataRouterStateContextVar.get()
    if state and getattr(state, "errors", None):
        matches = getattr(state, "matches", [])
        if matches:
            return state.errors.get(matches[-1].route.id)
    return None


def useAsyncValue():
    return None


def useAsyncError():
    return None


def useBlocker(_shouldBlock):
    return {"state": "unblocked", "proceed": lambda: None, "reset": lambda: None}


def useRoute(*_args, **_kwargs):
    return None


__all__ = [
    "useInRouterContext",
    "useHref",
    "useNavigate",
    "useLocation",
    "useNavigationType",
    "useMatch",
    "useResolvedPath",
    "useOutlet",
    "useOutletContext",
    "useParams",
    "useRoutes",
    "useNavigation",
    "useRevalidator",
    "useMatches",
    "useLoaderData",
    "useRouteLoaderData",
    "useActionData",
    "useRouteError",
    "useAsyncValue",
    "useAsyncError",
    "useBlocker",
    "useRoute",
]
