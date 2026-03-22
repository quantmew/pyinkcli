from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from fnmatch import fnmatch
from types import SimpleNamespace
from urllib.parse import urlparse


class NavigationType(Enum):
    POP = "POP"
    PUSH = "PUSH"
    REPLACE = "REPLACE"


@dataclass
class Path:
    pathname: str = "/"
    search: str = ""
    hash: str = ""
    state: object = None
    key: str = "default"
    unstable_mask: object = None


@dataclass
class Update:
    action: NavigationType
    location: Path


class Headers(dict):
    def __getitem__(self, key):
        return super().__getitem__(key if key in self else key.title())


class Response:
    def __init__(self, data=None, *, status: int = 200, statusText: str = "", headers: Headers | None = None):
        self.data = data
        self.status = status
        self.statusText = statusText
        self.headers = headers or Headers()


@dataclass
class DataWithResponseInit:
    data: object
    init: object
    type: str = "DataWithResponseInit"


@dataclass
class ErrorResponseImpl:
    status: int
    statusText: str
    data: object
    internal: bool


@dataclass
class RouteObject:
    id: str = ""
    path: str | None = None
    element: object = None
    children: list["RouteObject"] = field(default_factory=list)
    handle: object = None
    Component: object = None
    HydrateFallback: object = None
    ErrorBoundary: object = None
    hasErrorBoundary: bool = False


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
        self.entries = self.entries[: self.index + 1] + [
            createLocation(self.location.pathname, to if isinstance(to, dict) else {"pathname": to, "state": state})
        ]
        self.index += 1
        self._notify(NavigationType.PUSH)

    def replace(self, to, state):
        self.entries[self.index] = createLocation(
            self.location.pathname,
            to if isinstance(to, dict) else {"pathname": to, "state": state},
        )
        self._notify(NavigationType.REPLACE)

    def go(self, delta):
        self.index = max(0, min(len(self.entries) - 1, self.index + delta))
        self._notify(NavigationType.POP)

    def createHref(self, location):
        return createPath(location)

    def encodeLocation(self, value):
        parsed = urlparse(value)
        return {
            "pathname": parsed.path,
            "search": normalizeSearch(parsed.query),
            "hash": normalizeHash(parsed.fragment),
        }


def normalizePathname(pathname: str) -> str:
    return "/" + "/".join(part for part in pathname.split("/") if part)


def normalizeSearch(search: str) -> str:
    if not search:
        return ""
    return search if search.startswith("?") else "?" + search


def normalizeHash(hash_value: str) -> str:
    if not hash_value:
        return ""
    return hash_value if hash_value.startswith("#") else "#" + hash_value


def joinPaths(parts: list[str]) -> str:
    return normalizePathname("/".join(parts))


def createPath(path: dict) -> str:
    return f"{path.get('pathname', '/')}{path.get('search', '')}{path.get('hash', '')}"


def decodePath(path: str) -> str:
    return path.replace("%20", " ")


def stripBasename(pathname: str, basename: str) -> str | None:
    if pathname == basename:
        return "/"
    if pathname.startswith(basename + "/"):
        return pathname[len(basename) :]
    return None


def prependBasename(*, basename: str, pathname: str) -> str:
    return joinPaths([basename, pathname])


def isAbsoluteUrl(value: str) -> bool:
    parsed = urlparse(value)
    return bool(parsed.scheme and parsed.netloc)


isBrowser = False


def parseToInfo(to: str, basename: str):
    return {
        "absoluteURL": to,
        "isExternal": False,
        "to": to,
    }


def createLocation(current: str, next_location: dict | str, *, key: str = "default", unstable_mask=None) -> Path:
    if isinstance(next_location, str):
        parsed = urlparse(next_location)
        return Path(
            pathname=parsed.path or "/",
            search=normalizeSearch(parsed.query),
            hash=normalizeHash(parsed.fragment),
            key=key,
            unstable_mask=unstable_mask,
        )
    return Path(
        pathname=next_location.get("pathname", current),
        search=next_location.get("search", ""),
        hash=next_location.get("hash", ""),
        state=next_location.get("state"),
        key=key,
        unstable_mask=unstable_mask,
    )


def resolvePath(to: str, from_pathname: str = "/"):
    if to.startswith("/"):
        return {"pathname": normalizePathname(to)}
    base = from_pathname.rstrip("/")
    while to.startswith("../"):
        to = to[3:]
        base = base.rsplit("/", 1)[0] or "/"
    return {"pathname": joinPaths([base, to])}


def createMemoryHistory(options):
    return _MemoryHistory(options)


def compilePath(path: str):
    parts = [part for part in path.split("/") if part]
    compiled = []
    pattern = "^"
    for part in parts:
        pattern += "/"
        if part == "*":
            compiled.append({"paramName": "*"})
            pattern += "(?P<splat>.*)"
        elif part.startswith(":"):
            compiled.append({"paramName": part[1:].rstrip("?")})
            if part.endswith("?"):
                pattern += "(?P<%s>[^/]*)?" % part[1:-1]
            else:
                pattern += "(?P<%s>[^/]+)" % part[1:]
        else:
            pattern += re.escape(part)
    pattern += "$"
    regex = re.compile(pattern or "^/$")
    return regex, compiled


def matchPath(path: str, pathname: str):
    regex, compiled = compilePath(path)
    match = regex.match(pathname)
    if not match:
        return None
    params = match.groupdict()
    if "splat" in params:
        params["*"] = params.pop("splat")
    return {"params": params, "pathname": pathname, "pathnameBase": pathname}


def generatePath(path: str, params: dict | None = None) -> str:
    params = params or {}
    result = path
    for key, value in params.items():
        result = result.replace(f":{key}", str(value)).replace("*", str(value) if key == "*" else result)
    result = result.replace("/:lang?", "")
    return result


def href(path: str, params: dict | None = None) -> str:
    params = params or {}
    required = re.findall(r":([A-Za-z0-9_]+)\b(?!\?)", path)
    for key in required:
        if key not in params:
            raise ValueError(f"requires param '{key}'")
    result = path
    optional = re.findall(r":([A-Za-z0-9_]+)\?", path)
    for key in optional:
        result = result.replace(f"/:{key}?", f"/{params[key]}" if key in params else "")
    return generatePath(result, params)


def data(value, init=None):
    return DataWithResponseInit(value, {"status": init} if isinstance(init, int) else (init or {}))


def redirect(location: str, init=None):
    init = {"status": 302, **(init or {})}
    return Response(status=init["status"], statusText=init.get("statusText", ""), headers=Headers({"Location": location}))


def redirectDocument(location: str, init=None):
    response = redirect(location, init)
    response.headers["X-Remix-Reload-Document"] = "true"
    return response


def replace(location: str, init=None):
    response = redirect(location, init)
    response.headers["X-Remix-Replace"] = "true"
    return response


def createRedirectErrorDigest(response: Response) -> str:
    return f"REACT_ROUTER_ERROR:REDIRECT:{response.status}:{response.statusText}:{response.headers['Location']}:{response.headers.get('X-Remix-Reload-Document') == 'true'}:{response.headers.get('X-Remix-Replace') == 'true'}"


def decodeRedirectErrorDigest(digest: str):
    try:
        _, _, status, status_text, location, reload_document, replace_flag = digest.split(":", 6)
    except ValueError:
        return None
    return {
        "status": int(status),
        "statusText": status_text,
        "location": location,
        "reloadDocument": reload_document == "True",
        "replace": replace_flag == "True",
    }


def createRouteErrorResponseDigest(response) -> str:
    if isinstance(response, DataWithResponseInit):
        status = response.init.get("status", 200)
        status_text = response.init.get("statusText", "")
        payload = response.data
    else:
        status = response.status
        status_text = response.statusText
        payload = response.data
    return repr((status, status_text, payload))


def decodeRouteErrorResponseDigest(digest: str):
    status, status_text, payload = eval(digest)
    return ErrorResponseImpl(status, status_text, payload, True)


def isRouteErrorResponse(value) -> bool:
    return isinstance(value, ErrorResponseImpl) or (
        isinstance(value, dict)
        and isinstance(value.get("status"), int)
        and "statusText" in value
        and "internal" in value
    )


def throwIfPotentialCSRFAttack(headers: Headers, allowed_origins):
    origin = headers.get("origin")
    if origin is None:
        return
    parsed = urlparse(origin)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("`origin` header is not a valid URL")
    host = headers.get("x-forwarded-host") or headers.get("host")
    if allowed_origins:
        if not any(fnmatch(parsed.netloc, pattern.replace("*.", "*")) for pattern in allowed_origins):
            raise ValueError("host header does not match `origin` header")
    elif host != parsed.netloc:
        raise ValueError("host header does not match `origin` header")


def hydrationRouteProperties():
    return None
