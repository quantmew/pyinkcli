"""Translated subset of `react-router/lib/router/utils.ts`."""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass, field
from functools import cmp_to_key
from typing import Any

from pyinkcli.packages.react_router.router.history import Path, To, parsePath


def invariant(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def warning(condition: bool, message: str) -> None:
    if not condition:
        pass


_CONTEXT_SENTINEL = object()


def createContext(defaultValue: Any = _CONTEXT_SENTINEL) -> RouterContext:
    if defaultValue is _CONTEXT_SENTINEL:
        return RouterContext(has_default=False)
    return RouterContext(defaultValue)


@dataclass
class RouteObject:
    id: str
    caseSensitive: bool = False
    path: str | None = None
    index: bool | None = False
    element: Any = None
    Component: Any = None
    children: list[RouteObject] = field(default_factory=list)
    middleware: Any = None
    loader: Any = None
    action: Any = None
    hydrateFallbackElement: Any = None
    HydrateFallback: Any = None
    errorElement: Any = None
    ErrorBoundary: Any = None
    hasErrorBoundary: bool = False
    shouldRevalidate: Any = None
    handle: Any = None
    lazy: Any = None


@dataclass
class RouteMatch:
    params: dict[str, str | None]
    pathname: str
    pathnameBase: str
    route: RouteObject


@dataclass
class UIMatch:
    id: str
    pathname: str
    params: dict[str, str | None]
    data: Any = None
    loaderData: Any = None
    handle: Any = None


class Headers(dict[str, str]):
    def __init__(self, init: Any | None = None):
        super().__init__()
        if init is None:
            return
        if isinstance(init, Headers):
            for key, value in init.items():
                self[key] = value
            return
        if isinstance(init, dict):
            for key, value in init.items():
                self[str(key)] = str(value)
            return
        for key, value in init:
            self[str(key)] = str(value)

    def set(self, key: str, value: Any) -> None:
        self[str(key)] = str(value)


@dataclass
class Response:
    body: Any = None
    status: int = 200
    headers: Headers = field(default_factory=Headers)
    statusText: str = ""


@dataclass
class DataWithResponseInit:
    data: Any
    init: dict[str, Any] | None = None
    type: str = "DataWithResponseInit"


class ErrorResponseImpl:
    def __init__(
        self,
        status: int,
        statusText: str | None,
        data: Any,
        internal: bool = False,
    ):
        self.status = status
        self.statusText = statusText or ""
        self.internal = internal
        self.error = data if isinstance(data, Exception) else None
        self.data = str(data) if isinstance(data, Exception) else data


class RouterContext:
    def __init__(self, defaultValue: Any = None, *, has_default: bool = True):
        self.defaultValue = defaultValue
        self._has_default = has_default


class RouterContextProvider:
    def __init__(self, init: dict[RouterContext, Any] | None = None):
        self._map: dict[RouterContext, Any] = {}
        if init:
            for context, value in init.items():
                self.set(context, value)

    def get(self, context: RouterContext) -> Any:
        if context in self._map:
            return self._map[context]
        if context._has_default:
            return context.defaultValue
        raise ValueError("No value found for context")

    def set(self, context: RouterContext, value: Any) -> None:
        self._map[context] = value


@dataclass
class _RouteMeta:
    relativePath: str
    caseSensitive: bool
    childrenIndex: int
    route: RouteObject


@dataclass
class _RouteBranch:
    path: str
    score: int
    routesMeta: list[_RouteMeta]


_UNSUPPORTED_LAZY_ROUTE_OBJECT_KEYS = {
    "lazy",
    "caseSensitive",
    "path",
    "id",
    "index",
    "children",
}

_UNSUPPORTED_LAZY_ROUTE_FUNCTION_KEYS = {
    "lazy",
    "caseSensitive",
    "path",
    "id",
    "index",
    "middleware",
    "children",
}


def isUnsupportedLazyRouteObjectKey(key: str) -> bool:
    return key in _UNSUPPORTED_LAZY_ROUTE_OBJECT_KEYS


def isUnsupportedLazyRouteFunctionKey(key: str) -> bool:
    return key in _UNSUPPORTED_LAZY_ROUTE_FUNCTION_KEYS


def decodePath(value: str) -> str:
    try:
        return "/".join(
            urllib.parse.unquote(segment).replace("/", "%2F")
            for segment in value.split("/")
        )
    except Exception:
        warning(False, f'The URL path "{value}" could not be decoded.')
        return value


def stripBasename(pathname: str, basename: str) -> str | None:
    if basename == "/":
        return pathname
    if not pathname.lower().startswith(basename.lower()):
        return None
    start_index = len(basename) - 1 if basename.endswith("/") else len(basename)
    next_char = pathname[start_index:start_index + 1]
    if next_char and next_char != "/":
        return None
    return pathname[start_index:] or "/"


def prependBasename(*, basename: str, pathname: str) -> str:
    return basename if pathname == "/" else joinPaths([basename, pathname])


_ABSOLUTE_URL_REGEX = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.IGNORECASE)


def isAbsoluteUrl(url: str) -> bool:
    return bool(_ABSOLUTE_URL_REGEX.search(url))


def joinPaths(paths: list[str]) -> str:
    return re.sub(r"/+", "/", "/".join(paths))


def normalizePathname(pathname: str) -> str:
    return re.sub(r"^\/*", "/", re.sub(r"/+$", "", pathname))


def normalizeSearch(search: str) -> str:
    if not search or search == "?":
        return ""
    return search if search.startswith("?") else f"?{search}"


def normalizeHash(hash_value: str) -> str:
    if not hash_value or hash_value == "#":
        return ""
    return hash_value if hash_value.startswith("#") else f"#{hash_value}"


def data(
    payload: Any,
    init: int | dict[str, Any] | None = None,
) -> DataWithResponseInit:
    response_init = {"status": init} if isinstance(init, int) else init
    return DataWithResponseInit(payload, response_init)


def redirect(
    url: str,
    init: int | dict[str, Any] | None = 302,
) -> Response:
    response_init = {"status": init} if isinstance(init, int) else dict(init or {})
    if "status" not in response_init:
        response_init["status"] = 302

    headers = Headers(response_init.get("headers"))
    headers.set("Location", url)
    return Response(
        body=None,
        status=int(response_init["status"]),
        headers=headers,
        statusText=str(response_init.get("statusText", "")),
    )


def redirectDocument(
    url: str,
    init: int | dict[str, Any] | None = None,
) -> Response:
    response = redirect(url, init)
    response.headers.set("X-Remix-Reload-Document", "true")
    return response


def replace(
    url: str,
    init: int | dict[str, Any] | None = None,
) -> Response:
    response = redirect(url, init)
    response.headers.set("X-Remix-Replace", "true")
    return response


def isRouteErrorResponse(error: Any) -> bool:
    if error is None:
        return False
    if isinstance(error, dict):
        return (
            isinstance(error.get("status"), int)
            and isinstance(error.get("statusText"), str)
            and isinstance(error.get("internal"), bool)
            and "data" in error
        )
    return (
        isinstance(getattr(error, "status", None), int)
        and isinstance(getattr(error, "statusText", None), str)
        and isinstance(getattr(error, "internal", None), bool)
        and hasattr(error, "data")
    )


def getRoutePattern(matches: list[Any]) -> str:
    pattern = "/".join(
        path
        for path in (getattr(getattr(match, "route", None), "path", None) for match in matches)
        if path
    )
    return re.sub(r"/+", "/", pattern) or "/"


isBrowser = False


def parseToInfo(_to: Any, basename: str) -> dict[str, Any]:
    del basename
    if not isinstance(_to, str) or not isAbsoluteUrl(_to):
        return {
            "absoluteURL": None,
            "isExternal": False,
            "to": _to,
        }

    return {
        "absoluteURL": _to,
        "isExternal": False,
        "to": _to,
    }


def resolvePath(to: To, fromPathname: str = "/") -> dict[str, str]:
    if isinstance(to, str):
        parsed = parsePath(to)
    elif isinstance(to, Path):
        parsed = {"pathname": to.pathname, "search": to.search, "hash": to.hash}
    else:
        parsed = dict(to)

    to_pathname = parsed.get("pathname")
    search = parsed.get("search", "")
    hash_value = parsed.get("hash", "")

    if to_pathname:
        to_pathname = re.sub(r"/+", "/", to_pathname)
        if to_pathname.startswith("/"):
            pathname = _resolvePathname(to_pathname[1:], "/")
        else:
            pathname = _resolvePathname(to_pathname, fromPathname)
    else:
        pathname = fromPathname

    return {
        "pathname": pathname,
        "search": normalizeSearch(search),
        "hash": normalizeHash(hash_value),
    }


def _resolvePathname(relativePath: str, fromPathname: str) -> str:
    segments = re.sub(r"/+$", "", fromPathname).split("/")
    relative_segments = relativePath.split("/")
    for segment in relative_segments:
        if segment == "..":
            if len(segments) > 1:
                segments.pop()
        elif segment != ".":
            segments.append(segment)
    return "/".join(segments) if len(segments) > 1 else "/"


def _getInvalidPathError(char: str, field: str, dest: str, path: dict[str, Any]) -> str:
    return (
        f"Cannot include a '{char}' character in a manually specified "
        f"`to.{field}` field [{path!r}]. Please separate it out to the "
        f"`to.{dest}` field."
    )


def getPathContributingMatches(matches: list[RouteMatch]) -> list[RouteMatch]:
    return [
        match
        for index, match in enumerate(matches)
        if index == 0 or (match.route.path and len(match.route.path) > 0)
    ]


def getResolveToMatches(matches: list[RouteMatch]) -> list[str]:
    path_matches = getPathContributingMatches(matches)
    return [
        match.pathname if index == len(path_matches) - 1 else match.pathnameBase
        for index, match in enumerate(path_matches)
    ]


def convertRouteMatchToUiMatch(
    match: RouteMatch,
    loaderData: dict[str, Any],
) -> UIMatch:
    route = match.route
    return UIMatch(
        id=route.id,
        pathname=match.pathname,
        params=match.params,
        data=loaderData.get(route.id),
        loaderData=loaderData.get(route.id),
        handle=route.handle,
    )


def resolveTo(
    toArg: To,
    routePathnames: list[str],
    locationPathname: str,
    isPathRelative: bool = False,
) -> dict[str, str]:
    if isinstance(toArg, str):
        to = parsePath(toArg)
    else:
        to = dict(toArg)
        invariant(
            "pathname" not in to or "?" not in str(to["pathname"]),
            _getInvalidPathError("?", "pathname", "search", to),
        )
        invariant(
            "pathname" not in to or "#" not in str(to["pathname"]),
            _getInvalidPathError("#", "pathname", "hash", to),
        )
        invariant(
            "search" not in to or "#" not in str(to["search"]),
            _getInvalidPathError("#", "search", "hash", to),
        )

    is_empty_path = toArg == "" or to.get("pathname") == ""
    to_pathname = "/" if is_empty_path else to.get("pathname")

    if to_pathname is None:
        from_pathname = locationPathname
    else:
        route_pathname_index = len(routePathnames) - 1
        if not isPathRelative and str(to_pathname).startswith(".."):
            to_segments = str(to_pathname).split("/")
            while to_segments and to_segments[0] == "..":
                to_segments.pop(0)
                route_pathname_index -= 1
            to["pathname"] = "/".join(to_segments)
        from_pathname = routePathnames[route_pathname_index] if route_pathname_index >= 0 else "/"

    path = resolvePath(to, from_pathname)

    has_explicit_trailing_slash = bool(to_pathname and to_pathname != "/" and str(to_pathname).endswith("/"))
    has_current_trailing_slash = (is_empty_path or to_pathname == ".") and locationPathname.endswith("/")
    if not path["pathname"].endswith("/") and (has_explicit_trailing_slash or has_current_trailing_slash):
        path["pathname"] += "/"
    return path


def convertRoutesToDataRoutes(
    routes: list[RouteObject],
    mapRouteProperties: Any,
    parentPath: list[str] | None = None,
    manifest: dict[str, RouteObject] | None = None,
    allowInPlaceMutations: bool = False,
) -> list[RouteObject]:
    parentPath = [] if parentPath is None else parentPath
    manifest = {} if manifest is None else manifest
    data_routes: list[RouteObject] = []

    for index, route in enumerate(routes):
        tree_path = [*parentPath, str(index)]
        route_id = route.id if isinstance(route.id, str) and route.id else "-".join(tree_path)

        invariant(route.index is not True or not route.children, "Cannot specify children on an index route")
        invariant(
            allowInPlaceMutations or route_id not in manifest,
            f'Found a route id collision on id "{route_id}".  Route id\'s must be globally unique within Data Router usages',
        )

        next_route = route if allowInPlaceMutations else _clone_route(route)
        next_route.id = route_id

        if route.index is True:
            updates = mapRouteProperties(next_route)
            manifest[route_id] = _mergeRouteUpdates(next_route, updates)
            data_routes.append(next_route)
            continue

        next_route.children = []
        updates = mapRouteProperties(next_route)
        manifest[route_id] = _mergeRouteUpdates(next_route, updates)

        if route.children:
            next_route.children = convertRoutesToDataRoutes(
                route.children,
                mapRouteProperties,
                tree_path,
                manifest,
                allowInPlaceMutations,
            )

        data_routes.append(next_route)

    return data_routes


def _clone_route(route: RouteObject) -> RouteObject:
    return RouteObject(
        id=route.id,
        caseSensitive=route.caseSensitive,
        path=route.path,
        index=route.index,
        element=route.element,
        Component=route.Component,
        children=list(route.children),
        middleware=route.middleware,
        loader=route.loader,
        action=route.action,
        hydrateFallbackElement=route.hydrateFallbackElement,
        HydrateFallback=route.HydrateFallback,
        errorElement=route.errorElement,
        ErrorBoundary=route.ErrorBoundary,
        hasErrorBoundary=route.hasErrorBoundary,
        shouldRevalidate=route.shouldRevalidate,
        handle=route.handle,
        lazy=route.lazy,
    )


def _mergeRouteUpdates(route: RouteObject, updates: dict[str, Any] | None) -> RouteObject:
    if not updates:
        return route

    for key, value in updates.items():
        if key == "lazy" and isinstance(value, dict) and isinstance(route.lazy, dict):
            route.lazy = {**route.lazy, **value}
            continue
        setattr(route, key, value)

    return route


def matchRoutes(
    routes: list[RouteObject],
    locationArg: str | dict[str, Any],
    basename: str = "/",
) -> list[RouteMatch] | None:
    return matchRoutesImpl(routes, locationArg, basename, False)


def matchRoutesImpl(
    routes: list[RouteObject],
    locationArg: str | dict[str, Any],
    basename: str,
    allowPartial: bool,
) -> list[RouteMatch] | None:
    location = parsePath(locationArg) if isinstance(locationArg, str) else locationArg
    pathname = stripBasename(location.get("pathname", "/"), basename)
    if pathname is None:
        return None
    branches = flattenRoutes(routes)
    rankRouteBranches(branches)
    decoded = decodePath(pathname)
    for branch in branches:
        matches = matchRouteBranch(branch, decoded, allowPartial)
        if matches is not None:
            return matches
    return None


def flattenRoutes(
    routes: list[RouteObject],
    branches: list[_RouteBranch] | None = None,
    parentsMeta: list[_RouteMeta] | None = None,
    parentPath: str = "",
    hasParentOptionalSegments: bool = False,
) -> list[_RouteBranch]:
    branches = [] if branches is None else branches
    parentsMeta = [] if parentsMeta is None else parentsMeta

    def flattenRoute(
        route: RouteObject,
        index: int,
        route_has_parent_optional_segments: bool = hasParentOptionalSegments,
        relativePath: str | None = None,
    ) -> None:
        meta = _RouteMeta(
            relativePath=route.path or "" if relativePath is None else relativePath,
            caseSensitive=route.caseSensitive is True,
            childrenIndex=index,
            route=route,
        )

        if meta.relativePath.startswith("/"):
            if not meta.relativePath.startswith(parentPath) and route_has_parent_optional_segments:
                return
            invariant(
                meta.relativePath.startswith(parentPath),
                (
                    f'Absolute route path "{meta.relativePath}" nested under path '
                    f'"{parentPath}" is not valid.'
                ),
            )
            meta.relativePath = meta.relativePath[len(parentPath) :]

        path = joinPaths([parentPath, meta.relativePath])
        routesMeta = parentsMeta + [meta]

        if route.children:
            invariant(route.index is not True, f'Index routes must not have child routes. route path "{path}".')
            flattenRoutes(route.children, branches, routesMeta, path, route_has_parent_optional_segments)

        if route.path is None and not route.index:
            return

        branches.append(
            _RouteBranch(
                path=path,
                score=computeScore(path, route.index),
                routesMeta=routesMeta,
            )
        )

    for index, route in enumerate(routes):
        if route.path in ("", None) or "?" not in (route.path or ""):
            flattenRoute(route, index)
        else:
            for exploded in explodeOptionalSegments(route.path or ""):
                flattenRoute(route, index, True, exploded)

    return branches


def explodeOptionalSegments(path: str) -> list[str]:
    segments = path.split("/")
    if not segments:
        return []
    first, *rest = segments
    is_optional = first.endswith("?")
    required = re.sub(r"\?$", "", first)
    if not rest:
        return [required, ""] if is_optional else [required]
    rest_exploded = explodeOptionalSegments("/".join(rest))
    result = [
        required if subpath == "" else "/".join([required, subpath])
        for subpath in rest_exploded
    ]
    if is_optional:
        result.extend(rest_exploded)
    return ["/" if path.startswith("/") and exploded == "" else exploded for exploded in result]


def rankRouteBranches(branches: list[_RouteBranch]) -> None:
    def compare_branches(a: _RouteBranch, b: _RouteBranch) -> int:
        if a.score != b.score:
            return b.score - a.score
        return _compareIndexes(
            [meta.childrenIndex for meta in a.routesMeta],
            [meta.childrenIndex for meta in b.routesMeta],
        )

    branches.sort(key=cmp_to_key(compare_branches))


def _compareIndexes(a: list[int], b: list[int]) -> int:
    siblings = len(a) == len(b) and all(
        left == right for left, right in zip(a[:-1], b[:-1])
    )
    if siblings:
        return a[-1] - b[-1]
    return 0


def generatePath(
    originalPath: str,
    params: dict[str, Any] | None = None,
) -> str:
    params = {} if params is None else params
    path = originalPath
    if path.endswith("*") and path != "*" and not path.endswith("/*"):
        normalized_path = re.sub(r"\*$", "/*", path)
        warning(
            False,
            (
                f'Route path "{path}" will be treated as if it were '
                f'"{normalized_path}" because the `*` character must '
                "always follow a `/` in the pattern."
            ),
        )
        path = normalized_path

    prefix = "/" if path.startswith("/") else ""

    def stringify(value: Any) -> str:
        if value is None:
            return ""
        return value if isinstance(value, str) else str(value)

    segments: list[str] = []
    path_segments = re.split(r"/+", path)
    for index, segment in enumerate(path_segments):
        is_last_segment = index == len(path_segments) - 1
        if is_last_segment and segment == "*":
            segments.append(stringify(params.get("*")))
            continue

        key_match = re.match(r"^:([\w-]+)(\??)(.*)", segment)
        if key_match:
            key, optional, suffix = key_match.group(1), key_match.group(2), key_match.group(3)
            param = params.get(key)
            invariant(optional == "?" or param is not None, f'Missing ":{key}" param')
            segments.append(urllib.parse.quote(stringify(param), safe="") + suffix)
            continue

        segments.append(re.sub(r"\?+$", "", segment))

    return prefix + "/".join(segment for segment in segments if segment)


_param_re = re.compile(r"^:[\w-]+$")
_dynamic_segment_value = 3
_index_route_value = 2
_empty_segment_value = 1
_static_segment_value = 10
_splat_penalty = -2


def computeScore(path: str, index: bool | None) -> int:
    segments = path.split("/")
    initial_score = len(segments)
    if any(segment == "*" for segment in segments):
        initial_score += _splat_penalty
    if index:
        initial_score += _index_route_value
    score = initial_score
    for segment in segments:
        if segment == "*":
            continue
        if _param_re.match(segment):
            score += _dynamic_segment_value
        elif segment == "":
            score += _empty_segment_value
        else:
            score += _static_segment_value
    return score


def matchRouteBranch(
    branch: _RouteBranch,
    pathname: str,
    allowPartial: bool = False,
) -> list[RouteMatch] | None:
    matched_params: dict[str, str | None] = {}
    matched_pathname = "/"
    matches: list[RouteMatch] = []
    routes_meta = branch.routesMeta
    for index, meta in enumerate(routes_meta):
        end = index == len(routes_meta) - 1
        remaining_pathname = pathname if matched_pathname == "/" else pathname[len(matched_pathname) :] or "/"
        match = matchPath(
            {
                "path": meta.relativePath,
                "caseSensitive": meta.caseSensitive,
                "end": end,
            },
            remaining_pathname,
        )
        route = meta.route
        if not match and end and allowPartial and not routes_meta[-1].route.index:
            match = matchPath(
                {
                    "path": meta.relativePath,
                    "caseSensitive": meta.caseSensitive,
                    "end": False,
                },
                remaining_pathname,
            )
        if not match:
            return None

        matched_params.update(match["params"])
        matches.append(
            RouteMatch(
                params=dict(matched_params),
                pathname=joinPaths([matched_pathname, match["pathname"]]),
                pathnameBase=normalizePathname(joinPaths([matched_pathname, match["pathnameBase"]])),
                route=route,
            )
        )
        if match["pathnameBase"] != "/":
            matched_pathname = joinPaths([matched_pathname, match["pathnameBase"]])
    return matches


def matchPath(pattern: str | dict[str, Any], pathname: str) -> dict[str, Any] | None:
    if isinstance(pattern, str):
        pattern = {"path": pattern, "caseSensitive": False, "end": True}
    matcher, compiled_params = compilePath(
        pattern["path"],
        pattern.get("caseSensitive", False),
        pattern.get("end", True),
    )
    match = matcher.match(pathname)
    if not match:
        return None
    matched_pathname = match.group(0)
    pathname_base = re.sub(r"(.)/+$", r"\1", matched_pathname)
    capture_groups = list(match.groups())
    params: dict[str, str | None] = {}
    for index, param in enumerate(compiled_params):
        param_name = param["paramName"]
        is_optional = param.get("isOptional", False)
        if param_name == "*":
            splat_value = capture_groups[index] or ""
            pathname_base = re.sub(
                r"(.)/+$",
                r"\1",
                matched_pathname[: len(matched_pathname) - len(splat_value)],
            )
        value = capture_groups[index]
        if is_optional and not value:
            params[param_name] = None
        else:
            params[param_name] = (value or "").replace("%2F", "/")
    return {
        "params": params,
        "pathname": matched_pathname,
        "pathnameBase": pathname_base,
        "pattern": pattern,
    }


def compilePath(
    path: str,
    caseSensitive: bool = False,
    end: bool = True,
) -> tuple[re.Pattern[str], list[dict[str, Any]]]:
    warning(
        path == "*" or not path.endswith("*") or path.endswith("/*"),
        (
            f'Route path "{path}" will be treated as if it were '
            f'"{path[:-1]}/*" because the "*" character must follow "/" in the pattern.'
        ),
    )

    params: list[dict[str, Any]] = []
    regexp_source = "^"
    source = re.sub(r"/*\*?$", "", path)
    source = re.sub(r"^\/*", "/", source)
    source = re.sub(r"[\\.*+^${}|()[\]]", lambda m: "\\" + m.group(0), source)

    def replace_dynamic(match: re.Match[str]) -> str:
        param_name = match.group(1)
        is_optional = match.group(2) is not None
        params.append({"paramName": param_name, "isOptional": is_optional})
        if is_optional:
            next_char_index = match.end()
            next_char = source[next_char_index:next_char_index + 1]
            if next_char and next_char != "/":
                return r"/([^\/]*)"
            return r"(?:/([^\/]*))?"
        return r"/([^\/]+)"

    source = re.sub(r"/:([\w-]+)(\?)?", replace_dynamic, source)
    source = re.sub(r"/([\w-]+)\?(/|$)", r"(/\1)?\2", source)
    regexp_source += source

    if path.endswith("*"):
        params.append({"paramName": "*"})
        regexp_source += "(.*)$" if path in ("*", "/*") else r"(?:\/(.+)|\/*)$"
    elif end:
        regexp_source += r"\/*$"
    elif path not in ("", "/"):
        regexp_source += r"(?:(?=\/|$))"

    flags = 0 if caseSensitive else re.IGNORECASE
    return re.compile(regexp_source, flags), params
