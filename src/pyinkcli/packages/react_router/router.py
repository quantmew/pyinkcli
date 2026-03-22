"""Core router helpers and history primitives."""

from __future__ import annotations

import json
import random
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import SimpleNamespace
from typing import Any

from pyinkcli.component import createElement

from .context import RouteObject

isBrowser = False


def invariant(value: Any, message: str | None = None) -> None:
    if value is False or value is None:
        raise ValueError(message or "Invariant failed")


def warning(_cond: Any, _message: str) -> None:
    return None


@dataclass(frozen=True)
class Path:
    pathname: str = "/"
    search: str = ""
    hash: str = ""

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


@dataclass(frozen=True)
class Location(Path):
    state: Any = None
    key: str = "default"
    unstable_mask: Path | None = None

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


class Action(Enum):
    Pop = "POP"
    Push = "PUSH"
    Replace = "REPLACE"


@dataclass(frozen=True)
class Update:
    action: Action
    location: Location
    delta: int | None

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


@dataclass(frozen=True)
class RouteMatch:
    params: dict[str, str | None]
    pathname: str
    pathnameBase: str
    route: RouteObject

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


@dataclass(frozen=True)
class PathMatch:
    params: dict[str, str | None]
    pathname: str
    pathnameBase: str
    pattern: dict[str, Any]

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


@dataclass(frozen=True)
class UIMatch:
    id: str
    pathname: str
    params: dict[str, str | None]
    data: Any
    loaderData: Any
    handle: Any

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


def _get_mapping_value(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _path_parts(value: Any, default_pathname: str = "/") -> dict[str, Any]:
    if isinstance(value, str):
        return parsePath(value)
    if isinstance(value, Mapping):
        return dict(value)
    if value is None:
        return {"pathname": default_pathname, "search": "", "hash": ""}
    result: dict[str, Any] = {}
    for key in ("pathname", "search", "hash", "state", "key", "unstable_mask"):
        item = getattr(value, key, None)
        if item is not None:
            result[key] = item
    return result


def parsePath(path: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    if not path:
        return parsed

    hash_index = path.find("#")
    if hash_index >= 0:
        parsed["hash"] = path[hash_index:]
        path = path[:hash_index]

    search_index = path.find("?")
    if search_index >= 0:
        parsed["search"] = path[search_index:]
        path = path[:search_index]

    if path:
        parsed["pathname"] = path

    return parsed


def createPath(path: Mapping[str, Any] | Path) -> str:
    pathname = _get_mapping_value(path, "pathname", "/") or "/"
    search = _get_mapping_value(path, "search", "") or ""
    hash_value = _get_mapping_value(path, "hash", "") or ""
    if search and search != "?":
        pathname += search if search.startswith("?") else "?" + search
    if hash_value and hash_value != "#":
        pathname += hash_value if hash_value.startswith("#") else "#" + hash_value
    return pathname


def createLocation(
    current: str | Location | Mapping[str, Any],
    to: str | Mapping[str, Any] | Path,
    state: Any = None,
    key: str | None = None,
    unstable_mask: Path | None = None,
) -> Location:
    current_parts = _path_parts(current)
    to_parts = _path_parts(to, default_pathname=current_parts.get("pathname", "/"))
    pathname = to_parts.get("pathname", current_parts.get("pathname", "/")) or "/"
    search = to_parts.get("search", "")
    hash_value = to_parts.get("hash", "")
    next_state = state if state is not None else to_parts.get("state", None)
    next_key = (
        to_parts.get("key")
        or key
        or (to_parts["key"] if "key" in to_parts else None)
        or "default"
    )
    next_mask = unstable_mask if unstable_mask is not None else to_parts.get("unstable_mask")
    return Location(
        pathname=pathname,
        search=search,
        hash=hash_value,
        state=next_state,
        key=next_key,
        unstable_mask=next_mask,
    )


def _create_key() -> str:
    return "".join(random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(8))


def createMemoryHistory(options: Mapping[str, Any] | None = None):
    options = dict(options or {})
    initial_entries = options.get("initialEntries", ["/"])
    initial_index = options.get("initialIndex")
    v5_compat = bool(options.get("v5Compat", False))

    entries: list[Location] = [
        createLocation(
            "/",
            entry,
            None if isinstance(entry, str) else _get_mapping_value(entry, "state"),
            "default" if index == 0 else None,
            _get_mapping_value(entry, "unstable_mask"),
        )
        for index, entry in enumerate(initial_entries)
    ]
    if not entries:
        entries = [createLocation("/", "/")]

    def clamp_index(n: int) -> int:
        return min(max(n, 0), len(entries) - 1)

    index = clamp_index(len(entries) - 1 if initial_index is None else int(initial_index))
    action = Action.Pop
    listener: Callable[[Update], None] | None = None

    def get_current_location() -> Location:
        return entries[index]

    def create_memory_location(
        to: str | Mapping[str, Any] | Location | Path,
        state: Any = None,
        key: str | None = None,
        unstable_mask: Path | None = None,
    ) -> Location:
        location = createLocation(
            get_current_location().pathname if entries else "/",
            to,
            state,
            key,
            unstable_mask,
        )
        warning(
            location.pathname.startswith("/"),
            f"relative pathnames are not supported in memory history: {json.dumps(to, default=str)}",
        )
        return location

    class _MemoryHistory:
        def __init__(self):
            self._entries = entries

        @property
        def index(self) -> int:
            return index

        @property
        def action(self) -> Action:
            return action

        @property
        def location(self) -> Location:
            return get_current_location()

        def createHref(self, to: str | Mapping[str, Any] | Path) -> str:
            return to if isinstance(to, str) else createPath(to)

        def createURL(self, to: str | Mapping[str, Any] | Path):
            return _create_url(self.createHref(to))

        def encodeLocation(self, to: str | Mapping[str, Any] | Path):
            return _encode_location(to)

        def push(self, to: str | Mapping[str, Any] | Location | Path, state: Any = None) -> None:
            nonlocal action, index, entries
            action = Action.Push
            next_location = to if isinstance(to, Location) else create_memory_location(to, state)
            index += 1
            entries = entries[:index] + [next_location]
            self._entries = entries
            if v5_compat and listener:
                listener(Update(action=action, location=next_location, delta=1))

        def replace(self, to: str | Mapping[str, Any] | Location | Path, state: Any = None) -> None:
            nonlocal action, entries
            action = Action.Replace
            next_location = to if isinstance(to, Location) else create_memory_location(to, state)
            entries[index] = next_location
            self._entries = entries
            if v5_compat and listener:
                listener(Update(action=action, location=next_location, delta=0))

        def go(self, delta: int) -> None:
            nonlocal action, index
            action = Action.Pop
            next_index = clamp_index(index + delta)
            next_location = entries[next_index]
            index = next_index
            if listener:
                listener(Update(action=action, location=next_location, delta=delta))

        def listen(self, fn: Callable[[Update], None]):
            nonlocal listener
            listener = fn

            def unlisten() -> None:
                nonlocal listener
                if listener is fn:
                    listener = None

            return unlisten

    return _MemoryHistory()


def _create_url(href: str):
    return SimpleNamespace(href=href)


def _encode_location(to: str | Mapping[str, Any] | Path) -> dict[str, str]:
    path = parsePath(to) if isinstance(to, str) else dict(to)
    return {
        "pathname": path.get("pathname", ""),
        "search": path.get("search", ""),
        "hash": path.get("hash", ""),
    }


def joinPaths(paths: Iterable[str]) -> str:
    return re.sub(r"//+", "/", "/".join(paths))


def normalizePathname(pathname: str) -> str:
    return re.sub(r"^/*", "/", pathname).rstrip("/") or "/"


def normalizeSearch(search: str) -> str:
    if not search or search == "?":
        return ""
    return search if search.startswith("?") else "?" + search


def normalizeHash(hash_value: str) -> str:
    if not hash_value or hash_value == "#":
        return ""
    return hash_value if hash_value.startswith("#") else "#" + hash_value


def stripBasename(pathname: str, basename: str) -> str | None:
    if basename == "/":
        return pathname
    if not pathname.lower().startswith(basename.lower()):
        return None
    start_index = len(basename) - 1 if basename.endswith("/") else len(basename)
    next_char = pathname[start_index : start_index + 1]
    if next_char and next_char != "/":
        return None
    stripped = pathname[start_index:]
    return stripped or "/"


def prependBasename(*, basename: str, pathname: str) -> str:
    return basename if pathname == "/" else joinPaths([basename, pathname])


ABSOLUTE_URL_REGEX = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.I)


def isAbsoluteUrl(url: str) -> bool:
    return bool(ABSOLUTE_URL_REGEX.match(url))


def decodePath(value: str) -> str:
    try:
        from urllib.parse import unquote

        return "/".join(unquote(part).replace("/", "%2F") for part in value.split("/"))
    except Exception:
        warning(False, f"The URL path {value!r} could not be decoded because it is malformed.")
        return value


def resolvePath(to: str | Mapping[str, Any] | Path, fromPathname: str = "/") -> Path:
    parts = _path_parts(to, default_pathname="")
    to_pathname = parts.get("pathname")
    search = normalizeSearch(parts.get("search", ""))
    hash_value = normalizeHash(parts.get("hash", ""))

    if to_pathname:
        to_pathname = re.sub(r"//+", "/", to_pathname)
        if to_pathname.startswith("/"):
            pathname = _resolve_pathname(to_pathname[1:], "/")
        else:
            pathname = _resolve_pathname(to_pathname, fromPathname)
    else:
        pathname = fromPathname

    return Path(pathname=pathname, search=search, hash=hash_value)


def _resolve_pathname(relativePath: str, fromPathname: str) -> str:
    segments = re.sub(r"/+$", "", fromPathname).split("/")
    relative_segments = relativePath.split("/")
    for segment in relative_segments:
        if segment == "..":
            if len(segments) > 1:
                segments.pop()
        elif segment != ".":
            segments.append(segment)
    return "/".join(segments) if len(segments) > 1 else "/"


def _get_invalid_path_error(char: str, field: str, dest: str, path: Mapping[str, Any]) -> str:
    return (
        f"Cannot include a {char!r} character in a manually specified `to.{field}` field "
        f"[{json.dumps(dict(path), default=str)}].  Please separate it out to the `to.{dest}` field."
    )


def resolveTo(
    toArg: str | Mapping[str, Any] | Path,
    routePathnames: list[str],
    locationPathname: str,
    isPathRelative: bool = False,
) -> Path:
    if isinstance(toArg, str):
        to: dict[str, Any] = parsePath(toArg)
    else:
        to = _path_parts(toArg)
        invariant(
            not to.get("pathname") or "?" not in to.get("pathname", ""),
            _get_invalid_path_error("?", "pathname", "search", to),
        )
        invariant(
            not to.get("pathname") or "#" not in to.get("pathname", ""),
            _get_invalid_path_error("#", "pathname", "hash", to),
        )
        invariant(
            not to.get("search") or "#" not in to.get("search", ""),
            _get_invalid_path_error("#", "search", "hash", to),
        )

    isEmptyPath = toArg == "" or to.get("pathname") == ""
    toPathname = "/" if isEmptyPath else to.get("pathname")

    if toPathname is None:
        from_path = locationPathname
    else:
        routePathnameIndex = len(routePathnames) - 1
        if not isPathRelative and isinstance(toPathname, str) and toPathname.startswith(".."):
            toSegments = toPathname.split("/")
            while toSegments and toSegments[0] == "..":
                toSegments.pop(0)
                routePathnameIndex -= 1
            to["pathname"] = "/".join(toSegments)
        from_path = routePathnames[routePathnameIndex] if routePathnameIndex >= 0 else "/"

    path = resolvePath(to, from_path)
    hasExplicitTrailingSlash = bool(toPathname and toPathname != "/" and str(toPathname).endswith("/"))
    hasCurrentTrailingSlash = bool((isEmptyPath or toPathname == ".") and locationPathname.endswith("/"))
    if not path.pathname.endswith("/") and (hasExplicitTrailingSlash or hasCurrentTrailingSlash):
        path = Path(pathname=path.pathname + "/", search=path.search, hash=path.hash)
    return path


def getPathContributingMatches(matches: list[Any]):
    return [
        match
        for index, match in enumerate(matches)
        if index == 0 or (getattr(match.route, "path", None) and len(match.route.path) > 0)
    ]


def getResolveToMatches(matches: list[Any]) -> list[str]:
    pathMatches = getPathContributingMatches(matches)
    return [
        match.pathname if idx == len(pathMatches) - 1 else match.pathnameBase
        for idx, match in enumerate(pathMatches)
    ]


def compilePath(path: str, caseSensitive: bool = False, end: bool = True):
    invariant(
        path == "*" or not path.endswith("*") or path.endswith("/*"),
        f'Route path "{path}" will be treated as if it were "{path.replace("*", "/*")}" because the `*` character must always follow a `/` in the pattern.',
    )

    params: list[dict[str, Any]] = []
    regexpSource = re.sub(r"/\*?$", "", path)
    regexpSource = re.sub(r"^/*", "/", regexpSource)
    regexpSource = re.sub(r"[\\.*+^${}|()[\]]", r"\\\g<0>", regexpSource)
    regexpSource = "^" + regexpSource

    def replace_dynamic(match: re.Match[str]) -> str:
        paramName = match.group(1)
        isOptional = match.group(2) is not None
        params.append({"paramName": paramName, "isOptional": isOptional})
        if isOptional:
            next_char = match.string[match.end() : match.end() + 1]
            if next_char and next_char != "/":
                return "/([^/]*)"
            return "(?:/([^/]*))?"
        return "/([^/]+)"

    regexpSource = re.sub(r"/:([\w-]+)(\?)?", replace_dynamic, regexpSource)
    regexpSource = re.sub(r"/([\w-]+)\?(\/|$)", r"(/\1)?\2", regexpSource)

    if path.endswith("*"):
        params.append({"paramName": "*"})
        regexpSource += r"(.*)$" if path in ("*", "/*") else r"(?:\/(.+)|\/*)$"
    elif end:
        regexpSource += r"\/*$"
    elif path not in ("", "/"):
        regexpSource += r"(?:(?=\/|$))"

    flags = 0 if caseSensitive else re.I
    return re.compile(regexpSource, flags), params


def matchPath(
    pattern: str | Mapping[str, Any],
    pathname: str,
) -> PathMatch | None:
    if isinstance(pattern, str):
        pattern = {"path": pattern, "caseSensitive": False, "end": True}

    matcher, compiledParams = compilePath(
        pattern["path"],
        bool(pattern.get("caseSensitive")),
        bool(pattern.get("end", True)),
    )
    match = matcher.match(pathname)
    if not match:
        return None

    matchedPathname = match.group(0)
    pathnameBase = re.sub(r"(.)\/+$", r"\1", matchedPathname)
    captureGroups = list(match.groups())
    params: dict[str, str | None] = {}
    for index, compiled in enumerate(compiledParams):
        paramName = compiled["paramName"]
        isOptional = compiled.get("isOptional", False)
        value = captureGroups[index] if index < len(captureGroups) else None
        if paramName == "*":
            splatValue = value or ""
            pathnameBase = re.sub(r"(.)\/+$", r"\1", matchedPathname[: len(matchedPathname) - len(splatValue)])
        params[paramName] = None if (isOptional and not value) else (value or "").replace("%2F", "/")

    return PathMatch(
        params=params,
        pathname=matchedPathname,
        pathnameBase=pathnameBase,
        pattern=pattern,
    )


def generatePath(originalPath: str, params: Mapping[str, Any] | None = None) -> str:
    params = dict(params or {})
    path = originalPath
    if path.endswith("*") and path != "*" and not path.endswith("/*"):
        path = path[:-1] + "/*"

    prefix = "/" if path.startswith("/") else ""

    def stringify(value: Any) -> str:
        return "" if value is None else str(value)

    split_segments = [segment for segment in re.split(r"/+", path) if segment]
    segments = []
    for index, segment in enumerate(split_segments):
        is_last = index == len(split_segments) - 1
        if is_last and segment == "*":
            segments.append(stringify(params.get("*")))
            continue
        key_match = re.match(r"^:([\w-]+)(\??)(.*)", segment)
        if key_match:
            key, optional, suffix = key_match.groups()
            param = params.get(key)
            invariant(optional == "?" or param is not None, f'Missing ":{key}" param')
            segments.append((stringify(param) if param is not None else "") + suffix)
            continue
        segments.append(segment.replace("?", ""))
    segments = [segment for segment in segments if segment]
    return prefix + "/".join(segments) if segments else "/"
def _is_index_route(route: RouteObject) -> bool:
    return route.index is True


def _clone_route(route: RouteObject) -> RouteObject:
    return RouteObject(**{key: getattr(route, key) for key in vars(route)})


def _merge_route_updates(route: RouteObject, updates: Mapping[str, Any]) -> RouteObject:
    for key, value in updates.items():
        if key == "lazy" and isinstance(value, Mapping) and value is not None:
            existing = getattr(route, "lazy", None) or {}
            setattr(route, "lazy", {**existing, **dict(value)})
        else:
            setattr(route, key, value)
    return route


def convertRoutesToDataRoutes(
    routes: list[RouteObject],
    mapRouteProperties: Callable[[RouteObject], Mapping[str, Any]],
    parentPath: list[str] | None = None,
    manifest: dict[str, RouteObject] | None = None,
    allowInPlaceMutations: bool = False,
) -> list[RouteObject]:
    parentPath = list(parentPath or [])
    manifest = manifest if manifest is not None else {}
    converted: list[RouteObject] = []

    for index, route in enumerate(routes):
        treePath = parentPath + [str(index)]
        route_id = route.id if isinstance(route.id, str) and route.id else "-".join(treePath)
        invariant(route.index is not True or not route.children, "Cannot specify children on an index route")
        if not allowInPlaceMutations:
            invariant(route_id not in manifest, f'Found a route id collision on id "{route_id}".  Route id\'s must be globally unique within Data Router usages')

        current = route if allowInPlaceMutations else _clone_route(route)
        current.id = route_id

        if _is_index_route(current):
            current.children = None
        else:
            if current.children:
                current.children = convertRoutesToDataRoutes(
                    current.children,
                    mapRouteProperties,
                    treePath,
                    manifest,
                    allowInPlaceMutations,
                )
        updates = mapRouteProperties(current)
        current = _merge_route_updates(current, updates)
        manifest[route_id] = current
        converted.append(current)

    return converted


def _flatten_optional_segments(path: str) -> list[str]:
    segments = path.split("/")
    if not segments:
        return []
    first, *rest = segments
    is_optional = first.endswith("?")
    required = first[:-1] if is_optional else first
    if not rest:
        return [required] if not is_optional else [required, ""]
    rest_exploded = _flatten_optional_segments("/".join(rest))
    result = ["/".join([required, sub]).rstrip("/") if sub else required for sub in rest_exploded]
    if is_optional:
        result.extend(rest_exploded)
    return ["/" if path.startswith("/") and item == "" else item for item in result]


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


def _compute_score(path: str, index: bool | None) -> int:
    segments = path.split("/")
    score = len(segments)
    if "*" in segments:
        score -= 2
    if index:
        score += 2
    for segment in segments:
        if segment == "*":
            continue
        if re.fullmatch(r":[\w-]+", segment):
            score += 3
        elif segment == "":
            score += 1
        else:
            score += 10
    return score


def _compare_indexes(a: list[int], b: list[int]) -> int:
    siblings = len(a) == len(b) and a[:-1] == b[:-1]
    if siblings:
        return a[-1] - b[-1]
    return 0


def _flatten_routes(
    routes: list[RouteObject],
    branches: list[_RouteBranch] | None = None,
    parentsMeta: list[_RouteMeta] | None = None,
    parentPath: str = "",
    hasParentOptionalSegments: bool = False,
) -> list[_RouteBranch]:
    if branches is None:
        branches = []
    if parentsMeta is None:
        parentsMeta = []

    def flatten_route(route: RouteObject, index: int, relativePath: str | None = None):
        meta = _RouteMeta(
            relativePath=route.path or "" if relativePath is None else relativePath,
            caseSensitive=bool(route.caseSensitive),
            childrenIndex=index,
            route=route,
        )
        if meta.relativePath.startswith("/"):
            invariant(
                meta.relativePath.startswith(parentPath),
                f'Absolute route path "{meta.relativePath}" nested under path "{parentPath}" is not valid. An absolute child route path must start with the combined path of all its parent routes.',
            )
            meta.relativePath = meta.relativePath[len(parentPath) :]
        path = joinPaths([parentPath, meta.relativePath])
        routesMeta = parentsMeta + [meta]
        if route.children:
            invariant(route.index is not True, f"Index routes must not have child routes. Please remove all child routes from route path \"{path}\".")
            _flatten_routes(route.children, branches, routesMeta, path, hasParentOptionalSegments)
        if route.path is None and not route.index:
            return
        branches.append(_RouteBranch(path=path, score=_compute_score(path, route.index), routesMeta=routesMeta))

    for index, route in enumerate(routes):
        if route.path == "" or not route.path or "?" not in route.path:
            flatten_route(route, index)
        else:
            for exploded in _flatten_optional_segments(route.path):
                flatten_route(route, index, exploded)
    return branches


def _rank_route_branches(branches: list[_RouteBranch]) -> None:
    branches.sort(
        key=lambda branch: (
            -branch.score,
            branch.routesMeta[-1].childrenIndex,
        )
    )


def _match_route_branch(
    branch: _RouteBranch,
    pathname: str,
    allowPartial: bool = False,
) -> list[RouteMatch] | None:
    matchedParams: dict[str, str | None] = {}
    matchedPathname = "/"
    matches: list[RouteMatch] = []
    for index, meta in enumerate(branch.routesMeta):
        end = index == len(branch.routesMeta) - 1
        remainingPathname = pathname if matchedPathname == "/" else pathname[len(matchedPathname) :] or "/"
        match = matchPath({"path": meta.relativePath, "caseSensitive": meta.caseSensitive, "end": end}, remainingPathname)
        if not match and end and allowPartial and not branch.routesMeta[-1].route.index:
            match = matchPath({"path": meta.relativePath, "caseSensitive": meta.caseSensitive, "end": False}, remainingPathname)
        if not match:
            return None
        matchedParams.update(match.params)
        matches.append(
            RouteMatch(
                params=dict(matchedParams),
                pathname=joinPaths([matchedPathname, match.pathname]),
                pathnameBase=normalizePathname(joinPaths([matchedPathname, match.pathnameBase])),
                route=meta.route,
            )
        )
        if match.pathnameBase != "/":
            matchedPathname = joinPaths([matchedPathname, match.pathnameBase])
    return matches


def matchRoutes(
    routes: list[RouteObject],
    locationArg: Mapping[str, Any] | str,
    basename: str = "/",
):
    return matchRoutesImpl(routes, locationArg, basename, False)


def matchRoutesImpl(
    routes: list[RouteObject],
    locationArg: Mapping[str, Any] | str,
    basename: str,
    allowPartial: bool,
):
    location = parsePath(locationArg) if isinstance(locationArg, str) else _path_parts(locationArg)
    pathname = stripBasename(location.get("pathname", "/"), basename)
    if pathname is None:
        return None
    branches = _flatten_routes(routes)
    _rank_route_branches(branches)
    for branch in branches:
        matches = _match_route_branch(branch, decodePath(pathname), allowPartial)
        if matches is not None:
            return matches
    return None


def convertRouteMatchToUiMatch(match: RouteMatch, loaderData: Mapping[str, Any]) -> UIMatch:
    return UIMatch(
        id=match.route.id,
        pathname=match.pathname,
        params=match.params,
        data=loaderData.get(match.route.id),
        loaderData=loaderData.get(match.route.id),
        handle=match.route.handle,
    )


def getRoutePattern(matches: list[RouteMatch]) -> str:
    return re.sub(r"/\/*", "/", "/".join([match.route.path for match in matches if match.route.path])) or "/"


def parseToInfo(_to: str | Mapping[str, Any] | Path, basename: str):
    to = _to if isinstance(_to, str) else createPath(_to)
    if not isinstance(to, str) or not isAbsoluteUrl(to):
        return {"absoluteURL": None, "isExternal": False, "to": _to}
    absoluteURL = to
    isExternal = False
    return {"absoluteURL": absoluteURL, "isExternal": isExternal, "to": to}


def href(path: str, params: Mapping[str, Any] | None = None) -> str:
    params = dict(params or {})

    def trimTrailingSplat(path_value: str) -> str:
        i = len(path_value) - 1
        if i < 0 or path_value[i] not in {"*", "/"}:
            return path_value
        i -= 1
        while i >= 0 and path_value[i] == "/":
            i -= 1
        return path_value[: i + 1]

    result = trimTrailingSplat(path)

    def replace(match: re.Match[str]) -> str:
        param = match.group(1)
        is_optional = match.group(2) == "?"
        value = params.get(param)
        if value is None and not is_optional:
            raise ValueError(f"Path '{path}' requires param '{param}' but it was not provided")
        return "" if value is None else "/" + str(value)

    result = re.sub(r"/:([\w-]+)(\?)?", replace, result)
    if path.endswith("*"):
        value = params.get("*")
        if value is not None:
            result += "/" + str(value)
    return result or "/"


def _normalize_path_for_href(path: str) -> str:
    return path if path.startswith("/") else "/" + path


def isUnsupportedLazyRouteObjectKey(key: str) -> bool:
    return key in {"lazy", "caseSensitive", "path", "id", "index", "children"}


def isUnsupportedLazyRouteFunctionKey(key: str) -> bool:
    return key in {"lazy", "caseSensitive", "path", "id", "index", "middleware", "children"}


def isRouteErrorResponse(error: Any) -> bool:
    return (
        error is not None
        and isinstance(_get_mapping_value(error, "status", None), int)
        and isinstance(_get_mapping_value(error, "statusText", ""), str)
        and isinstance(_get_mapping_value(error, "internal", False), bool)
        and ("data" in error if isinstance(error, Mapping) else hasattr(error, "data"))
    )


@dataclass
class DataWithResponseInit:
    data: Any
    init: dict[str, Any] | None = None
    type: str = field(default="DataWithResponseInit", init=False)


def data(value: Any, init: int | Mapping[str, Any] | None = None):
    return DataWithResponseInit(value, {"status": init} if isinstance(init, int) else dict(init or {}) or None)


class Headers:
    def __init__(self, init: Any = None):
        self._items: dict[str, tuple[str, list[str]]] = {}
        if init is None:
            return
        if isinstance(init, Headers):
            for key, value in init.items():
                self.append(key, value)
            return
        if isinstance(init, Mapping):
            for key, value in init.items():
                if isinstance(value, (list, tuple)):
                    for item in value:
                        self.append(str(key), str(item))
                else:
                    self.set(str(key), str(value))
            return
        for key, value in init:
            self.append(str(key), str(value))

    def _key(self, key: str) -> str:
        return key.lower()

    def get(self, key: str, default: Any = None) -> Any:
        item = self._items.get(self._key(key))
        if item is None:
            return default
        return item[1][-1]

    def set(self, key: str, value: Any) -> None:
        self._items[self._key(key)] = (key, [str(value)])

    def append(self, key: str, value: Any) -> None:
        lower = self._key(key)
        if lower in self._items:
            original, values = self._items[lower]
            values.append(str(value))
            self._items[lower] = (original, values)
        else:
            self._items[lower] = (key, [str(value)])

    def delete(self, key: str) -> None:
        self._items.pop(self._key(key), None)

    def has(self, key: str) -> bool:
        return self._key(key) in self._items

    def items(self):
        for original, values in self._items.values():
            for value in values:
                yield original, value

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and self.has(key)

    def __getitem__(self, key: str) -> str:
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def __iter__(self):
        for key, _ in self.items():
            yield key

    def __len__(self) -> int:
        return sum(len(values) for _, values in self._items.values())

    def __repr__(self) -> str:
        return f"Headers({dict(self.items())!r})"


class Response:
    def __init__(
        self,
        body: Any = None,
        init: Mapping[str, Any] | None = None,
        *,
        status: int = 200,
        statusText: str = "",
        headers: Any = None,
    ):
        if isinstance(init, Mapping):
            status = int(init.get("status", status))
            statusText = str(init.get("statusText", statusText))
            headers = init.get("headers", headers)
        self.body = body
        self.status = int(status)
        self.statusText = statusText
        self.headers = Headers(headers)

    def clone(self) -> "Response":
        return Response(self.body, status=self.status, statusText=self.statusText, headers=self.headers)

    @classmethod
    def error(cls) -> "Response":
        return cls(None, status=500, statusText="Error")

    @classmethod
    def redirect(cls, url: str, status: int = 302) -> "Response":
        headers = Headers({"Location": url})
        return cls(None, status=status, headers=headers)


def redirect(url: str, init: int | Mapping[str, Any] = 302) -> Response:
    response_init: dict[str, Any]
    if isinstance(init, int):
        response_init = {"status": init}
    else:
        response_init = dict(init)
    response_init.setdefault("status", 302)
    headers = Headers(response_init.get("headers"))
    headers.set("Location", url)
    return Response(None, status=response_init["status"], statusText=response_init.get("statusText", ""), headers=headers)


def redirectDocument(url: str, init: int | Mapping[str, Any] | None = None) -> Response:
    response = redirect(url, 302 if init is None else init)
    response.headers.set("X-Remix-Reload-Document", "true")
    return response


def replace(url: str, init: int | Mapping[str, Any] | None = None) -> Response:
    response = redirect(url, 302 if init is None else init)
    response.headers.set("X-Remix-Replace", "true")
    return response


class ErrorResponseImpl:
    def __init__(self, status: int, statusText: str | None, data: Any, internal: bool = False):
        self.status = status
        self.statusText = statusText or ""
        self.internal = internal
        self.data = str(data) if isinstance(data, Exception) else data


def createRedirectErrorDigest(response: Response) -> str:
    return "REACT_ROUTER_ERROR:REDIRECT:" + json.dumps(
        {
            "status": response.status,
            "statusText": response.statusText,
            "location": response.headers.get("Location"),
            "reloadDocument": response.headers.get("X-Remix-Reload-Document") == "true",
            "replace": response.headers.get("X-Remix-Replace") == "true",
        }
    )


def decodeRedirectErrorDigest(digest: str):
    prefix = "REACT_ROUTER_ERROR:REDIRECT:{"
    if digest.startswith(prefix):
        try:
            parsed = json.loads(digest[len("REACT_ROUTER_ERROR:REDIRECT:") :])
            if (
                isinstance(parsed, dict)
                and isinstance(parsed.get("status"), int)
                and isinstance(parsed.get("statusText"), str)
                and isinstance(parsed.get("location"), str)
                and isinstance(parsed.get("reloadDocument"), bool)
                and isinstance(parsed.get("replace"), bool)
            ):
                return parsed
        except Exception:
            return None
    return None


def createRouteErrorResponseDigest(response: DataWithResponseInit | Response) -> str:
    status = 500
    statusText = ""
    data_value: Any = None
    if isinstance(response, DataWithResponseInit):
        status = response.init.get("status", status) if response.init else status
        statusText = response.init.get("statusText", statusText) if response.init else statusText
        data_value = response.data
    else:
        status = response.status
        statusText = response.statusText
        data_value = None
    return "REACT_ROUTER_ERROR:ROUTE_ERROR_RESPONSE:" + json.dumps(
        {"status": status, "statusText": statusText, "data": data_value}
    )


def decodeRouteErrorResponseDigest(digest: str):
    prefix = "REACT_ROUTER_ERROR:ROUTE_ERROR_RESPONSE:{"
    if digest.startswith(prefix):
        try:
            parsed = json.loads(digest[len("REACT_ROUTER_ERROR:ROUTE_ERROR_RESPONSE:") :])
            if isinstance(parsed, dict) and isinstance(parsed.get("status"), int) and isinstance(parsed.get("statusText"), str):
                return ErrorResponseImpl(parsed["status"], parsed["statusText"], parsed.get("data"))
        except Exception:
            return None
    return None


def _routish_component(*children: Any, **props: Any):
    return createElement("ink-text", *(children or ("" ,)), **props)


def getRoutePattern(matches: list[RouteMatch]):
    return re.sub(r"/\/*", "/", "/".join(filter(None, (m.route.path for m in matches)))) or "/"


def generatePathAlias(path: str, params: Mapping[str, Any] | None = None) -> str:
    return generatePath(path, params)


def parseToInfoAlias(_to: str | Mapping[str, Any] | Path, basename: str):
    return parseToInfo(_to, basename)


__all__ = [
    "Action",
    "Path",
    "Location",
    "Update",
    "RouteMatch",
    "PathMatch",
    "UIMatch",
    "Headers",
    "Response",
    "DataWithResponseInit",
    "ErrorResponseImpl",
    "createLocation",
    "createMemoryHistory",
    "createPath",
    "parsePath",
    "joinPaths",
    "normalizePathname",
    "normalizeSearch",
    "normalizeHash",
    "stripBasename",
    "prependBasename",
    "isAbsoluteUrl",
    "isBrowser",
    "resolvePath",
    "resolveTo",
    "getPathContributingMatches",
    "getResolveToMatches",
    "compilePath",
    "matchPath",
    "matchRoutes",
    "matchRoutesImpl",
    "generatePath",
    "decodePath",
    "convertRoutesToDataRoutes",
    "convertRouteMatchToUiMatch",
    "getRoutePattern",
    "parseToInfo",
    "href",
    "isUnsupportedLazyRouteObjectKey",
    "isUnsupportedLazyRouteFunctionKey",
    "isRouteErrorResponse",
    "data",
    "redirect",
    "redirectDocument",
    "replace",
    "createRedirectErrorDigest",
    "decodeRedirectErrorDigest",
    "createRouteErrorResponseDigest",
    "decodeRouteErrorResponseDigest",
    "invariant",
    "warning",
]
