from __future__ import annotations

from dataclasses import replace as dc_replace

from ...component import RenderableNode, createElement
from .router import RouteObject


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
    return {
        "Component": None,
        "HydrateFallback": None,
        "ErrorBoundary": None,
        "hasErrorBoundary": route.ErrorBoundary is not None,
        "element": createElement(route.Component) if route.Component else route.element,
        "hydrateFallbackElement": createElement(route.HydrateFallback) if route.HydrateFallback else None,
        "errorElement": createElement(route.ErrorBoundary) if route.ErrorBoundary else None,
    }


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


__all__ = [
    "convertRoutesToDataRoutes",
    "createRoutesFromChildren",
    "createRoutesFromElements",
    "hydrationRouteProperties",
    "mapRouteProperties",
]
