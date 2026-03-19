"""Component stack helpers aligned with ReactFiberComponentStack responsibilities."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler


def getSourceForTarget(
    _reconciler: "_Reconciler",
    target: Any,
    display_name: str,
) -> Optional[list[Any]]:
    try:
        source_file = inspect.getsourcefile(target) or inspect.getfile(target)
        _, line_number = inspect.getsourcelines(target)
    except (OSError, TypeError):
        return None
    if source_file is None:
        return None
    return [display_name, str(Path(source_file).resolve()), int(line_number), 1]


def makeCallSite(
    _reconciler: "_Reconciler",
    display_name: str,
    source: Optional[list[Any]],
) -> Optional[list[Any]]:
    if source is None:
        return None
    return [
        display_name,
        source[1],
        source[2],
        source[3],
        source[2],
        source[3],
        False,
    ]


def serializeDevtoolsOwnerStack(reconciler: "_Reconciler") -> Optional[list[dict[str, Any]]]:
    if not reconciler._owner_component_stack:
        return None
    owners: list[dict[str, Any]] = []
    ancestry: list[dict[str, Any]] = []
    for entry in reversed(reconciler._owner_component_stack):
        ancestry.insert(0, entry)
        owners.append(
            {
                "displayName": entry["displayName"],
                "id": entry["id"],
                "key": entry["key"],
                "env": None,
                "stack": buildDevtoolsStack(reconciler, ancestry),
                "type": entry["elementType"],
            }
        )
    return owners


def buildDevtoolsStack(
    reconciler: "_Reconciler",
    entries: list[dict[str, Any]],
    *,
    current_entry: Optional[dict[str, Any]] = None,
) -> Optional[list[list[Any]]]:
    frames: list[list[Any]] = []
    if current_entry is not None:
        current_frame = makeCallSite(
            reconciler,
            current_entry["displayName"],
            current_entry.get("source"),
        )
        if current_frame is not None:
            frames.append(current_frame)
    for entry in reversed(entries):
        frame = makeCallSite(reconciler, entry["displayName"], entry.get("source"))
        if frame is not None:
            frames.append(frame)
    return frames or None


def getCurrentOwnerSource(reconciler: "_Reconciler") -> Optional[list[Any]]:
    if not reconciler._owner_component_stack:
        return None
    return reconciler._clone_inspected_value(
        reconciler._owner_component_stack[-1].get("source")
    )


__all__ = [
    "buildDevtoolsStack",
    "getCurrentOwnerSource",
    "getSourceForTarget",
    "makeCallSite",
    "serializeDevtoolsOwnerStack",
]
