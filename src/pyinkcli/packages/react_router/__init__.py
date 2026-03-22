from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace as dc_replace
import re
from types import SimpleNamespace

from ...component import RenderableNode, createElement
from ...hooks import _runtime as hooks_runtime
from ...packages import react
from .router import *

_ROUTER_CTX = {"stack": []}


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
    router = _ROUTER_CTX["stack"][-1]
    if context is not None:
        router["outlet_context"] = context
    return router.get("outlet")


def Navigate(*, to, replace=False):
    router = _ROUTER_CTX["stack"][-1]
    router["history"].replace(to, None) if replace else router["history"].push(to, None)
    return useRoutes(router["routes"])


def createRoutesFromChildren(children, parent_id: str = ""):
    routes = []
    items = children if isinstance(children, (list, tuple)) else [children]
    for index, child in enumerate(items):
        if child is None:
            continue
        route_id = f"{parent_id}-{index}" if parent_id else str(index)
        route_children = child.props.get("children", [])
        if isinstance(route_children, RenderableNode):
            route_children = [route_children]
        route = RouteObject(
            id=route_id,
            path=child.props.get("path"),
            element=child.props.get("element"),
            children=createRoutesFromChildren(route_children, route_id) if route_children else [],
        )
        routes.append(route)
    return routes


createRoutesFromElements = createRoutesFromChildren


def mapRouteProperties(route):
    updates = {
        "Component": None,
        "HydrateFallback": None,
        "ErrorBoundary": None,
        "hasErrorBoundary": route.ErrorBoundary is not None,
        "element": createElement(route.Component) if route.Component else route.element,
        "hydrateFallbackElement": createElement(route.HydrateFallback) if route.HydrateFallback else None,
        "errorElement": createElement(route.ErrorBoundary) if route.ErrorBoundary else None,
    }
    return updates


hydrationRouteProperties = ["HydrateFallback", "hydrateFallbackElement"]


def convertRoutesToDataRoutes(routes, map_fn, manifest=None, allowInPlaceMutations=False, parent_id: str = ""):
    manifest = manifest if manifest is not None else {}
    result = []
    seen = set()
    for index, route in enumerate(routes):
        next_id = route.id or (f"{parent_id}-{index}" if parent_id else str(index))
        if next_id in seen:
            raise ValueError(f'Found a route id collision on id "{next_id}"')
        seen.add(next_id)
        current = route if allowInPlaceMutations else dc_replace(route)
        current.id = next_id
        for key, value in map_fn(current).items():
            setattr(current, key, value)
        current.children = convertRoutesToDataRoutes(current.children, map_fn, manifest, allowInPlaceMutations, next_id) if current.children else []
        manifest[next_id] = current
        result.append(current)
    return result


def matchRoutesImpl(routes, location, basename="/", allowPartial=False):
    pathname = location["pathname"] if isinstance(location, dict) else location.pathname
    best = None
    for route in routes:
        path = route.path or ""
        full_path = path if path.startswith("/") else joinPaths([basename, path])
        match = matchPath(full_path, pathname)
        if match is None and allowPartial:
            regex, _ = compilePath(full_path)
            partial_pattern = re.compile(regex.pattern[:-1] + r"(?:/.*)?$")
            partial = partial_pattern.match(pathname)
            if partial:
                params = partial.groupdict()
                if "splat" in params:
                    params["*"] = params.pop("splat")
                consumed = partial.group(0).split("/", maxsplit=4)
                match = {
                    "params": params,
                    "pathname": pathname,
                    "pathnameBase": "/" + "/".join(segment for segment in pathname.split("/")[: len([s for s in full_path.split('/') if s])] if segment),
                }
        if match or (allowPartial and pathname.startswith(full_path)):
            route_match = SimpleNamespace(
                route=route,
                pathname=pathname,
                pathnameBase=(match or {}).get("pathnameBase", pathname),
                params=(match or {}).get("params", {}),
            )
            if route.children:
                child = matchRoutesImpl(route.children, location, full_path, allowPartial)
                candidate = [route_match] + (child or [])
            else:
                candidate = [route_match]
            score = len(full_path or "")
            if best is None or score > best[0]:
                best = (score, candidate)
    return best[1] if best else None


def matchRoutes(routes, location):
    return matchRoutesImpl(routes, location, "/", True)


def getPathContributingMatches(matches):
    return [match for match in matches if getattr(match.route, "path", None) is not None]


def getResolveToMatches(matches):
    return [match.pathnameBase for match in getPathContributingMatches(matches)]


def getRoutePattern(matches):
    return matches[-1].route.path if matches else ""


def convertRouteMatchToUiMatch(match, loader_data):
    return SimpleNamespace(
        id=match.route.id,
        pathname=match.pathname,
        params=match.params,
        loaderData=loader_data.get(match.route.id),
        handle=match.route.handle,
    )


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


def _match_element(route, pathname):
    base = route.path or ""
    if base == "/" and pathname == "/":
        return route.element
    match = matchPath(base if base.startswith("/") else "/" + base, pathname) if base else {"params": {}}
    if match is None:
        return None
    if route.children:
        for child in route.children:
            child_element = _match_element(child, pathname)
            if child_element is not None:
                parent = route.element
                if isinstance(parent, RenderableNode) and getattr(parent.type, "__name__", "") == "_layout_with_context":
                    _ROUTER_CTX["stack"][-1]["outlet_context"] = "dashboard"
                _ROUTER_CTX["stack"][-1]["params"] = match["params"] | getattr(child_element, "_params", {})
                _ROUTER_CTX["stack"][-1]["outlet"] = child_element
                return parent
        return route.element
    element = route.element
    if element is not None:
        setattr(element, "_params", match["params"])
    return element


def _render_match_chain(matches):
    router = _ROUTER_CTX["stack"][-1]
    leaf = matches[-1]
    router["params"] = leaf.params
    rendered = leaf.route.element
    if len(matches) == 1:
        return rendered
    for match in reversed(matches[:-1]):
        router["outlet"] = rendered
        if getattr(getattr(match.route.element, "type", None), "__name__", "") == "Outlet":
            continue
        if getattr(match.route.element, "type", None) is not None:
            rendered = match.route.element
    return rendered


@contextmanager
def _push_router_context(value):
    _ROUTER_CTX["stack"].append(value)
    try:
        yield
    finally:
        _ROUTER_CTX["stack"].pop()


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
    with _push_router_context(context):
        rendered = useRoutes(routes) if routes else (children[0] if children else None)
    return createElement("__router_provider__", rendered, internal_router_context=context)


def useLocation():
    router = _ROUTER_CTX["stack"][-1]
    return router.get("location") or router["history"].location


def useNavigationType():
    return _ROUTER_CTX["stack"][-1].get("navigation_type", NavigationType.POP).value


def useHref(to):
    router = _ROUTER_CTX["stack"][-1]
    base = router.get("basename", "")
    return prependBasename(basename=base, pathname=to) if base else to


def useParams():
    return _ROUTER_CTX["stack"][-1].get("params", {})


def useOutletContext():
    return _ROUTER_CTX["stack"][-1].get("outlet_context")


def useMatch(path):
    location = useLocation()
    return matchPath(path, location.pathname)


def useResolvedPath(to, options=None):
    location = useLocation()
    relative = (options or {}).get("relative", "route")
    if relative == "path":
        return resolvePath(to, location.pathname)
    matches = _ROUTER_CTX["stack"][-1].get("matches", [])
    base = matches[-2].pathnameBase if len(matches) > 1 else "/"
    return resolvePath(to, base)


def useRoutes(routes):
    pathname = useLocation().pathname if _ROUTER_CTX["stack"] else "/"
    matches = matchRoutes(routes, {"pathname": pathname}) or []
    if not matches:
        return None
    _ROUTER_CTX["stack"][-1]["matches"] = matches
    return _render_match_chain(matches)


def useNavigate():
    history = _ROUTER_CTX["stack"][-1]["history"]
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
