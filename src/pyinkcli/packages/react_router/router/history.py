"""Translated subset of `react-router/lib/router/history.ts`."""

from __future__ import annotations

import random
import string
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Union


class Action(str, Enum):
    Pop = "POP"
    Push = "PUSH"
    Replace = "REPLACE"


@dataclass
class Path:
    pathname: str = "/"
    search: str = ""
    hash: str = ""


@dataclass
class Location(Path):
    state: Any = None
    key: str = "default"
    unstable_mask: Path | None = None


@dataclass
class Update:
    action: Action
    location: Location
    delta: int | None


Listener = Callable[[Update], None]
To = Union[str, dict[str, Any], Path, Location]


def _warning(condition: bool, message: str) -> None:
    if not condition:
        pass


def _create_key() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


def createPath(path: dict[str, str] | Path) -> str:
    pathname = path.get("pathname", "/") if isinstance(path, dict) else path.pathname
    search = path.get("search", "") if isinstance(path, dict) else path.search
    hash_value = path.get("hash", "") if isinstance(path, dict) else path.hash
    if search and search != "?":
        pathname += search if search.startswith("?") else f"?{search}"
    if hash_value and hash_value != "#":
        pathname += hash_value if hash_value.startswith("#") else f"#{hash_value}"
    return pathname


def parsePath(path: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    if path:
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


def createLocation(
    current: str | Location,
    to: To,
    state: Any = None,
    key: str | None = None,
    unstable_mask: Path | None = None,
) -> Location:
    base_pathname = current if isinstance(current, str) else current.pathname
    if isinstance(to, Location):
        parsed: dict[str, Any] = {
            "pathname": to.pathname,
            "search": to.search,
            "hash": to.hash,
            "state": to.state,
            "key": to.key,
            "unstable_mask": to.unstable_mask,
        }
    elif isinstance(to, Path):
        parsed = {
            "pathname": to.pathname,
            "search": to.search,
            "hash": to.hash,
        }
    elif isinstance(to, str):
        parsed = parsePath(to)
    else:
        parsed = dict(to)

    return Location(
        pathname=parsed.get("pathname", base_pathname),
        search=parsed.get("search", ""),
        hash=parsed.get("hash", ""),
        state=parsed.get("state", state),
        key=parsed.get("key", key or _create_key()),
        unstable_mask=parsed.get("unstable_mask", unstable_mask),
    )


class MemoryHistory:
    def __init__(
        self,
        *,
        initialEntries: list[str | dict[str, Any]] | None = None,
        initialIndex: int | None = None,
        v5Compat: bool = False,
    ) -> None:
        entries = initialEntries or ["/"]
        self._entries: list[Location] = []
        self._entries: list[Location] = [
            self._create_memory_location(
                entry,
                None if isinstance(entry, str) else entry.get("state"),
                "default" if index == 0 else None,
                None if isinstance(entry, str) else entry.get("unstable_mask"),
            )
            for index, entry in enumerate(entries)
        ]
        self._index = min(max(initialIndex if initialIndex is not None else len(self._entries) - 1, 0), len(self._entries) - 1)
        self._action = Action.Pop
        self._listeners: list[Listener] = []
        self._v5_compat = v5Compat

    @property
    def index(self) -> int:
        return self._index

    @property
    def action(self) -> Action:
        return self._action

    @property
    def location(self) -> Location:
        return self._entries[self._index]

    def _create_memory_location(
        self,
        to: To,
        state: Any = None,
        key: str | None = None,
        unstable_mask: Path | None = None,
    ) -> Location:
        current_pathname = self.location.pathname if self._entries else "/"
        location = createLocation(current_pathname, to, state, key, unstable_mask)
        _warning(
            location.pathname.startswith("/"),
            f"relative pathnames are not supported in memory history: {to!r}",
        )
        return location

    def createHref(self, to: To) -> str:
        if isinstance(to, str):
            return to
        if isinstance(to, (Path, Location)):
            return createPath({"pathname": to.pathname, "search": to.search, "hash": to.hash})
        return createPath(to)

    def encodeLocation(self, to: To) -> dict[str, str]:
        parsed = parsePath(to) if isinstance(to, str) else {
            "pathname": getattr(to, "pathname", "") if not isinstance(to, dict) else to.get("pathname", ""),
            "search": getattr(to, "search", "") if not isinstance(to, dict) else to.get("search", ""),
            "hash": getattr(to, "hash", "") if not isinstance(to, dict) else to.get("hash", ""),
        }
        return {
            "pathname": parsed.get("pathname", ""),
            "search": parsed.get("search", ""),
            "hash": parsed.get("hash", ""),
        }

    def push(self, to: To, state: Any = None, opts: Any = None) -> None:
        del opts
        self._action = Action.Push
        next_location = to if isinstance(to, Location) else self._create_memory_location(to, state)
        self._index += 1
        self._entries[self._index :] = [next_location]
        if self._v5_compat:
            self._notify(next_location, 1)

    def replace(self, to: To, state: Any = None, opts: Any = None) -> None:
        del opts
        self._action = Action.Replace
        next_location = to if isinstance(to, Location) else self._create_memory_location(to, state)
        self._entries[self._index] = next_location
        if self._v5_compat:
            self._notify(next_location, 0)

    def go(self, delta: int) -> None:
        self._action = Action.Pop
        next_index = min(max(self._index + delta, 0), len(self._entries) - 1)
        delta_value = next_index - self._index
        self._index = next_index
        self._notify(self.location, delta_value)

    def listen(self, listener: Listener) -> Callable[[], None]:
        self._listeners.append(listener)

        def unlisten() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unlisten

    def _notify(self, location: Location, delta: int | None) -> None:
        update = Update(action=self._action, location=location, delta=delta)
        for listener in list(self._listeners):
            listener(update)


def createMemoryHistory(options: dict[str, Any] | None = None) -> MemoryHistory:
    options = options or {}
    return MemoryHistory(
        initialEntries=options.get("initialEntries"),
        initialIndex=options.get("initialIndex"),
        v5Compat=options.get("v5Compat", False),
    )
