"""Tree reflection and devtools query helpers aligned with reconciler responsibilities."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler
    from pyinkcli.hooks._runtime import HookFiber


def getFiberNode(
    reconciler: _Reconciler,
    node_id: str,
) -> HookFiber | None:
    fiber_nodes = getattr(reconciler, "_fiber_nodes", None)
    if not isinstance(fiber_nodes, dict):
        return None
    return fiber_nodes.get(node_id)


def _get_fiber_display_name(fiber: HookFiber) -> str:
    element_type = getattr(fiber, "element_type", None)
    if element_type == "root":
        return "Root"
    if element_type == "host":
        pending_props = getattr(fiber, "pending_props", None) or {}
        node_name = pending_props.get("nodeName")
        if isinstance(node_name, str) and node_name:
            return node_name
    component_id = getattr(fiber, "component_id", "")
    if isinstance(component_id, str) and ":" in component_id:
        return component_id.split(":", 1)[0]
    return str(element_type or component_id or "Unknown")


def getDevtoolsTreeSnapshot(reconciler: _Reconciler) -> dict[str, Any]:
    nodes = [
        dict(node)
        for node in reconciler._devtools_tree_snapshot.get("nodes", [])
    ]
    return {
        "rootID": reconciler._devtools_tree_snapshot.get("rootID", "root"),
        "nodes": nodes,
    }


def getDevtoolsDisplayName(
    reconciler: _Reconciler,
    node_id: str,
) -> str | None:
    fiber = getFiberNode(reconciler, node_id)
    if fiber is not None:
        return _get_fiber_display_name(fiber)
    for node in reconciler._devtools_tree_snapshot.get("nodes", []):
        if node.get("id") == node_id:
            return node.get("displayName")
    return None


def getDevtoolsProfilingData(reconciler: _Reconciler) -> dict[str, Any]:
    return {
        "dataForRoots": [
            {
                "rootID": reconciler._devtools_tree_snapshot.get("rootID", "root"),
                "displayName": "Root",
                "commitData": [],
                "initialTreeBaseDurations": [],
            }
        ],
        "rendererID": id(reconciler),
        "timelineData": None,
    }


def getDevtoolsPathForElement(
    reconciler: _Reconciler,
    node_id: str,
) -> list[dict[str, Any]] | None:
    fiber = getFiberNode(reconciler, node_id)
    if fiber is not None:
        path: list[dict[str, Any]] = []
        current = fiber
        while current is not None and getattr(current, "component_id", None) != "root":
            parent = getattr(current, "return_fiber", None)
            index = 0
            if parent is not None:
                sibling = parent.child
                while sibling is not None and sibling is not current:
                    index += 1
                    sibling = sibling.sibling
            path.append(
                {
                    "displayName": _get_fiber_display_name(current),
                    "key": getattr(current, "key", None),
                    "index": index,
                }
            )
            current = parent
        path.reverse()
        return path

    nodes = reconciler._devtools_tree_snapshot.get("nodes", [])
    nodes_by_id = {node.get("id"): node for node in nodes}
    current = nodes_by_id.get(node_id)
    if current is None:
        return None
    path: list[dict[str, Any]] = []
    while current is not None and current.get("parentID") is not None:
        parent_id = current.get("parentID")
        siblings = [
            node for node in nodes
            if node.get("parentID") == parent_id
        ]
        index = next(
            (
                position
                for position, node in enumerate(siblings)
                if node.get("id") == current.get("id")
            ),
            0,
        )
        path.append(
            {
                "displayName": current.get("displayName"),
                "key": current.get("key"),
                "index": index,
            }
        )
        current = nodes_by_id.get(parent_id)
    path.reverse()
    return path


def getDevtoolsOwnersList(
    reconciler: _Reconciler,
    node_id: str,
) -> list[dict[str, Any]]:
    element = reconciler._devtools_inspected_elements.get(node_id)
    if element is None:
        return []
    owners = element.get("owners")
    if not isinstance(owners, list):
        return []
    return reconciler._clone_inspected_value(owners)


def getDevtoolsElementIDForHostInstance(
    reconciler: _Reconciler,
    target: Any,
) -> str | None:
    return reconciler._devtools_host_instance_ids.get(id(target))


def getDevtoolsSuspenseNodeIDForHostInstance(
    reconciler: _Reconciler,
    target: Any,
) -> str | None:
    node_id = getDevtoolsElementIDForHostInstance(reconciler, target)
    if node_id is None:
        return None
    return reconciler._devtools_nearest_suspense_boundary_by_node.get(node_id)


def hasDevtoolsNode(
    reconciler: _Reconciler,
    node_id: str,
) -> bool:
    if getFiberNode(reconciler, node_id) is not None:
        return True
    return any(
        node.get("id") == node_id
        for node in reconciler._devtools_tree_snapshot.get("nodes", [])
    )


def isMostRecentlyInspectedElement(
    reconciler: _Reconciler,
    node_id: str,
) -> bool:
    return reconciler._devtools_most_recently_inspected_id == node_id


def mergeDevtoolsInspectedPath(
    reconciler: _Reconciler,
    path: list[Any],
) -> None:
    current = reconciler._devtools_currently_inspected_paths
    for key in path:
        current = current.setdefault(key, {})


def getDevtoolsNode(
    reconciler: _Reconciler,
    node_id: str,
) -> dict[str, Any] | None:
    fiber = getFiberNode(reconciler, node_id)
    if fiber is not None:
        parent = getattr(fiber, "return_fiber", None)
        return {
            "id": getattr(fiber, "component_id", node_id),
            "parentID": getattr(parent, "component_id", None),
            "displayName": _get_fiber_display_name(fiber),
            "elementType": getattr(fiber, "element_type", None),
            "key": getattr(fiber, "key", None),
            "isErrorBoundary": False,
        }
    for node in reconciler._devtools_tree_snapshot.get("nodes", []):
        if node.get("id") == node_id:
            return node
    return None


def findNearestDevtoolsAncestor(
    reconciler: _Reconciler,
    node_id: str,
    *,
    predicate: Callable[[dict[str, Any]], bool],
) -> str | None:
    current_id: str | None = node_id
    while current_id is not None:
        node = getDevtoolsNode(reconciler, current_id)
        if node is None:
            return None
        if predicate(node):
            return current_id
        current_id = node.get("parentID")
    return None


__all__ = [
    "findNearestDevtoolsAncestor",
    "getFiberNode",
    "getDevtoolsDisplayName",
    "getDevtoolsElementIDForHostInstance",
    "getDevtoolsNode",
    "getDevtoolsOwnersList",
    "getDevtoolsPathForElement",
    "getDevtoolsProfilingData",
    "getDevtoolsSuspenseNodeIDForHostInstance",
    "getDevtoolsTreeSnapshot",
    "hasDevtoolsNode",
    "isMostRecentlyInspectedElement",
    "mergeDevtoolsInspectedPath",
]
