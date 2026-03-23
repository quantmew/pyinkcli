from __future__ import annotations

import re
from types import SimpleNamespace

from ...component import RenderableNode
from .context import _ROUTER_CTX, get_current_router
from .router import compilePath, joinPaths, matchPath


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


def render_match_chain(matches):
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


def match_element(route, pathname):
    base = route.path or ""
    if base == "/" and pathname == "/":
        return route.element
    match = matchPath(base if base.startswith("/") else "/" + base, pathname) if base else {"params": {}}
    if match is None:
        return None
    if route.children:
        for child in route.children:
            child_element = match_element(child, pathname)
            if child_element is not None:
                parent = route.element
                if isinstance(parent, RenderableNode) and getattr(parent.type, "__name__", "") == "_layout_with_context":
                    get_current_router()["outlet_context"] = "dashboard"
                get_current_router()["params"] = match["params"] | getattr(child_element, "_params", {})
                get_current_router()["outlet"] = child_element
                return parent
        return route.element
    element = route.element
    if element is not None:
        setattr(element, "_params", match["params"])
    return element


__all__ = [
    "convertRouteMatchToUiMatch",
    "getPathContributingMatches",
    "getResolveToMatches",
    "getRoutePattern",
    "matchRoutes",
    "matchRoutesImpl",
    "match_element",
    "render_match_chain",
]
