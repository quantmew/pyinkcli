"""Reconciler instance state and facade helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pyinkcli.packages.react_reconciler.ReactFiberHostContext import getRootHostContext
from pyinkcli.hooks._runtime import HookFiber
from pyinkcli.packages.react_reconciler.ReactWorkTags import HostRoot

if TYPE_CHECKING:
    from pyinkcli.packages.ink.dom import DOMElement
    from pyinkcli.packages.ink.host_config import ReconcilerHostConfig
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler


class DevtoolsForcedError(RuntimeError):
    """Synthetic error used to force error boundaries from devtools."""


def initializeReconcilerState(
    reconciler: _Reconciler,
    root_node: DOMElement,
) -> None:
    reconciler.root_node = root_node
    reconciler._root_fiber = HookFiber(
        component_id="root",
        tag=HostRoot,
        element_type="root",
        state_node=root_node,
    )
    reconciler._fiber_nodes = {"root": reconciler._root_fiber}
    reconciler._current_fiber = None
    reconciler._current_fiber_stack = []
    reconciler._host_context_stack = [getRootHostContext()]
    reconciler._owner_component_stack = []
    reconciler._error_boundary_stack = []
    reconciler._suspense_boundary_stack = []
    reconciler._class_component_instances = {}
    reconciler._visited_class_component_ids = set()
    reconciler._pending_class_component_commit_callbacks = []
    reconciler._pending_component_did_catch = []
    reconciler._deferred_component_did_catch = []
    reconciler._commit_phase_recovery_requested = False
    reconciler._devtools_container = None
    reconciler._devtools_forced_error_boundaries = set()
    reconciler._devtools_forced_error_boundary_states = {}
    reconciler._devtools_forced_suspense_boundaries = set()
    reconciler._devtools_nearest_error_boundary_by_node = {}
    reconciler._devtools_nearest_suspense_boundary_by_node = {}
    reconciler._devtools_prop_overrides = {}
    reconciler._devtools_effective_props = {}
    reconciler._next_devtools_effective_props = None
    reconciler._devtools_inspected_elements = {}
    reconciler._next_devtools_inspected_elements = None
    reconciler._devtools_inspected_element_fingerprints = {}
    reconciler._next_devtools_inspected_element_fingerprints = None
    reconciler._devtools_most_recently_inspected_id = None
    reconciler._devtools_has_element_updated_since_last_inspected = False
    reconciler._devtools_currently_inspected_paths = {}
    reconciler._devtools_last_copied_value = None
    reconciler._devtools_last_logged_element = None
    reconciler._devtools_stored_globals = {}
    reconciler._devtools_backend_notification_log = []
    reconciler._devtools_host_instance_ids = {}
    reconciler._next_devtools_host_instance_ids = None
    reconciler._devtools_tracked_path = None
    reconciler._devtools_tree_snapshot = {
        "rootID": "root",
        "nodes": [
            {
                "id": "root",
                "parentID": None,
                "displayName": "Root",
                "elementType": "root",
                "key": None,
                "isErrorBoundary": False,
            }
        ],
    }
    reconciler._next_devtools_tree_snapshot = None
    reconciler._host_config = None
    reconciler._on_commit = None
    reconciler._on_immediate_commit = None
    reconciler._attached_host_refs = {}
    reconciler._render_suspended = False
    reconciler._suspended_lanes_this_render = 0
    reconciler._current_work_budget = None
    reconciler._prepared_effects = {
        "mutation": [],
        "layout": [],
        "passive": [],
    }
    reconciler._last_prepared_commit = None


def setCommitHandlers(
    reconciler: _Reconciler,
    *,
    on_commit: Callable[[], None] | None = None,
    on_immediate_commit: Callable[[], None] | None = None,
) -> None:
    reconciler._on_commit = on_commit
    reconciler._on_immediate_commit = on_immediate_commit


def pushCurrentFiber(
    reconciler: _Reconciler,
    fiber: HookFiber,
) -> None:
    reconciler._fiber_nodes[fiber.component_id] = fiber
    reconciler._current_fiber_stack.append(fiber)
    reconciler._current_fiber = fiber


def popCurrentFiber(
    reconciler: _Reconciler,
) -> HookFiber | None:
    if not reconciler._current_fiber_stack:
        reconciler._current_fiber = None
        return None
    popped = reconciler._current_fiber_stack.pop()
    reconciler._current_fiber = (
        reconciler._current_fiber_stack[-1] if reconciler._current_fiber_stack else None
    )
    return popped


def configureHost(
    reconciler: _Reconciler,
    host_config: ReconcilerHostConfig | None,
) -> None:
    reconciler._host_config = host_config


def normalizeHookEditPath(
    _reconciler: _Reconciler,
    hook_id: int | None,
    path: list[Any],
) -> list[Any] | None:
    if hook_id is None:
        return list(path) if path else None
    return [hook_id, *path]


def createDevtoolsForcedError() -> Exception:
    return DevtoolsForcedError("DevTools forced error")


def getComponentInstanceID(
    _reconciler: _Reconciler,
    component_type: Any,
    vnode: Any,
    path: tuple[Any, ...],
) -> str:
    component_name = getattr(component_type, "_component_name", None)
    if component_name is None:
        component_name = getattr(component_type, "displayName", None)
    if component_name is None:
        component_name = getattr(component_type, "__name__", repr(component_type))

    key = vnode.key if vnode.key is not None else ""
    return f"{component_name}:{'.'.join(str(part) for part in path)}:{key}"


def getComponentDisplayName(
    _reconciler: _Reconciler,
    component_type: Any,
) -> str:
    display_name = getattr(component_type, "_component_name", None)
    if display_name is None:
        display_name = getattr(component_type, "displayName", None)
    if display_name is None:
        display_name = getattr(component_type, "__name__", repr(component_type))
    return str(display_name)


def isComponentTypeErrorBoundary(
    _reconciler: _Reconciler,
    component_type: type[Any],
) -> bool:
    return callable(getattr(component_type, "getDerivedStateFromError", None))


__all__ = [
    "configureHost",
    "createDevtoolsForcedError",
    "DevtoolsForcedError",
    "getComponentDisplayName",
    "getComponentInstanceID",
    "initializeReconcilerState",
    "isComponentTypeErrorBoundary",
    "normalizeHookEditPath",
    "popCurrentFiber",
    "pushCurrentFiber",
    "setCommitHandlers",
]
