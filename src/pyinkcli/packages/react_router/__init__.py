from __future__ import annotations

from types import SimpleNamespace

from ...component import RenderableNode, createElement
from ...hooks import _runtime as hooks_runtime
from ...packages import react
from .context import _ROUTER_CTX, get_current_router, push_router_context
from . import routes as _routes_module
from .matching import (
    convertRouteMatchToUiMatch,
    getPathContributingMatches,
    getResolveToMatches,
    getRoutePattern,
    matchRoutes,
    matchRoutesImpl,
    render_match_chain,
)
from .routes import (
    convertRoutesToDataRoutes,
    createRoutesFromChildren,
    createRoutesFromElements,
    hydrationRouteProperties,
    mapRouteProperties,
)
from .router import *

hydrationRouteProperties = _routes_module.hydrationRouteProperties


def createContext(default=None):
    marker = object() if default is None else default
    return SimpleNamespace(default=default, marker=marker)


class RouterContextProvider:
    def __init__(self):
        self._values = {}

    def set(self, context, value):
        self._values[id(context)] = value

    def get(self, context):
        if id(context) in self._values:
            return self._values[id(context)]
        if context.default is not None:
            return context.default
        raise ValueError("No value found for context")


def Route(**props):
    return createElement("__router_route__", **props)


def Routes(*children, location=None):
    return createElement("__router_routes__", *children, location=location)


def Outlet(*, context=None):
    router = get_current_router()
    if context is not None:
        router["outlet_context"] = context
    return router.get("outlet")


def Navigate(*, to, replace=False):
    router = get_current_router()
    router["history"].replace(to, None) if replace else router["history"].push(to, None)
    router["location"] = router["history"].location
    return useRoutes(router["routes"])


def isUnsupportedLazyRouteObjectKey(key):
    return key in {"path", "children"}


def isUnsupportedLazyRouteFunctionKey(key):
    return key in {"middleware"}


class _MemoryHistory:
    def __init__(self, options):
        self.entries = [createLocation("/", entry) for entry in options.get("initialEntries", ["/"])]
        self.index = options.get("initialIndex", len(self.entries) - 1)
        self.listeners = []

    @property
    def location(self):
        return self.entries[self.index]

    def listen(self, listener):
        self.listeners.append(listener)
        return lambda: self.listeners.remove(listener)

    def _notify(self, action):
        update = Update(action, self.location)
        for listener in list(self.listeners):
            listener(update)

    def push(self, to, state):
        self.entries = self.entries[: self.index + 1] + [createLocation(self.location.pathname, to if isinstance(to, dict) else {"pathname": to, "state": state})]
        self.index += 1
        self._notify(NavigationType.PUSH)

    def replace(self, to, state):
        self.entries[self.index] = createLocation(self.location.pathname, to if isinstance(to, dict) else {"pathname": to, "state": state})
        self._notify(NavigationType.REPLACE)

    def go(self, delta):
        self.index = max(0, min(len(self.entries) - 1, self.index + delta))
        self._notify(NavigationType.POP)

    def createHref(self, location):
        return createPath(location)

    def encodeLocation(self, value):
        parsed = urlparse(value)
        return {"pathname": parsed.path, "search": normalizeSearch(parsed.query), "hash": normalizeHash(parsed.fragment)}


def createMemoryHistory(options):
    return _MemoryHistory(options)


def MemoryRouter(*children, basename="", initialEntries=None):
    history = createMemoryHistory({"initialEntries": initialEntries or ["/"]})
    if basename:
        stripped = stripBasename(history.location.pathname, basename)
        if stripped is not None:
            history.entries[history.index].pathname = stripped
    routes = []
    location_override = None
    for child in children:
        if isinstance(child, RenderableNode) and (child.type == "__router_routes__" or getattr(child.type, "__name__", "") == "Routes"):
            routes = createRoutesFromChildren(child.children)
            location_override = child.props.get("location")
    context = {
        "basename": basename,
        "history": history,
        "location": createLocation(history.location.pathname, location_override) if location_override else history.location,
        "navigation_type": history.listeners and NavigationType.POP or NavigationType.POP,
        "routes": routes,
        "params": {},
        "outlet_context": None,
        "outlet": None,
    }
    with push_router_context(context):
        rendered = useRoutes(routes) if routes else (children[0] if children else None)
    return createElement("__router_provider__", rendered, internal_router_context=context)


def useLocation():
    router = get_current_router()
    return router.get("location") or router["history"].location


def useNavigationType():
    return get_current_router().get("navigation_type", NavigationType.POP).value


def useHref(to):
    router = get_current_router()
    base = router.get("basename", "")
    return prependBasename(basename=base, pathname=to) if base else to


def useParams():
    return get_current_router().get("params", {})


def useOutletContext():
    return get_current_router().get("outlet_context")


def useMatch(path):
    location = useLocation()
    return matchPath(path, location.pathname)


def useResolvedPath(to, options=None):
    location = useLocation()
    relative = (options or {}).get("relative", "route")
    if relative == "path":
        return resolvePath(to, location.pathname)
    matches = get_current_router().get("matches", [])
    base = matches[-2].pathnameBase if len(matches) > 1 else "/"
    return resolvePath(to, base)


def useRoutes(routes):
    pathname = useLocation().pathname if _ROUTER_CTX["stack"] else "/"
    matches = matchRoutes(routes, {"pathname": pathname}) or []
    if not matches:
        return None
    get_current_router()["matches"] = matches
    return render_match_chain(matches)


def useNavigate():
    history = get_current_router()["history"]
    return lambda to, replace=False: history.replace(to, None) if replace else history.push(to, None)


__all__ = [
    "DataWithResponseInit",
    "ErrorResponseImpl",
    "Headers",
    "MemoryRouter",
    "Navigate",
    "Outlet",
    "Path",
    "Response",
    "Route",
    "RouterContextProvider",
    "RouteObject",
    "Routes",
    "Update",
    "compilePath",
    "convertRouteMatchToUiMatch",
    "convertRoutesToDataRoutes",
    "createContext",
    "createLocation",
    "createMemoryHistory",
    "createPath",
    "createRedirectErrorDigest",
    "createRouteErrorResponseDigest",
    "createRoutesFromChildren",
    "createRoutesFromElements",
    "data",
    "decodePath",
    "decodeRedirectErrorDigest",
    "decodeRouteErrorResponseDigest",
    "generatePath",
    "getPathContributingMatches",
    "getResolveToMatches",
    "getRoutePattern",
    "href",
    "hydrationRouteProperties",
    "isAbsoluteUrl",
    "isBrowser",
    "isRouteErrorResponse",
    "isUnsupportedLazyRouteFunctionKey",
    "isUnsupportedLazyRouteObjectKey",
    "joinPaths",
    "mapRouteProperties",
    "matchPath",
    "matchRoutes",
    "matchRoutesImpl",
    "normalizeHash",
    "normalizePathname",
    "normalizeSearch",
    "parseToInfo",
    "prependBasename",
    "redirect",
    "redirectDocument",
    "replace",
    "resolvePath",
    "stripBasename",
    "throwIfPotentialCSRFAttack",
    "useHref",
    "useMatch",
    "useNavigate",
    "useNavigationType",
    "useOutletContext",
    "useParams",
    "useResolvedPath",
    "useRoutes",
    "useLocation",
]
