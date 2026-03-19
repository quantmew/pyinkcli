"""Reconciler for pyinkcli."""

from __future__ import annotations

import inspect
import json
import threading
import traceback
import array as array_module
import asyncio
import concurrent.futures
import datetime as datetime_module
import enum
import re
from contextlib import ExitStack
from collections import abc as collections_abc
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Literal, Optional, Union

from pyinkcli._component_runtime import (
    _Fragment,
    _Component,
    _create_component_instance,
    _is_component_class,
    _merge_component_props,
    createElement,
    isElement,
    is_component,
    renderComponent,
)
from pyinkcli._suspense_runtime import SuspendSignal
from pyinkcli.dom import (
    AccessibilityInfo,
    DOMElement,
    DOMNode,
    TextNode,
    appendChildNode,
    createNode,
    createTextNode,
    emitLayoutListeners,
    insertBeforeNode,
    removeChildNode,
    setAttribute,
    setStyle,
    setTextNodeValue,
)
from pyinkcli.styles import Styles, apply_styles
from pyinkcli.hooks._runtime import (
    _begin_component_render,
    _batched_updates_runtime,
    _consume_pending_rerender_priority,
    _delete_hook_state_path,
    _discrete_updates_runtime,
    _end_component_render,
    _finish_hook_state,
    _get_hook_state_snapshot,
    _override_hook_state,
    _rename_hook_state_path,
)

if TYPE_CHECKING:
    from pyinkcli.component import RenderableNode

UpdatePriority = Literal["default", "discrete", "render_phase"]


class _DevtoolsForcedError(Exception):
    """Synthetic error used to force error boundaries from devtools."""


@dataclass
class ReconcilerHostConfig:
    get_current_component: Callable[[], Optional["RenderableNode | Callable"]]
    perform_render: Callable[[Any], None]
    wait_for_render_flush: Callable[[Optional[float]], None]
    request_render: Callable[[UpdatePriority, bool], None]


@dataclass
class ReconcilerContainer:
    container: DOMElement
    tag: int = 0
    hydrate: bool = False
    pending_element: Optional["RenderableNode"] = None
    pending_callback: Optional[Callable[[], None]] = None
    work_scheduled: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)
    rerender_requested: bool = False
    rerender_running: bool = False
    pending_rerender_priority: UpdatePriority = "default"
    current_render_priority: UpdatePriority = "default"


class _Reconciler:
    """
    Custom reconciler for rendering components to the terminal DOM.

    Similar to React's reconciler but adapted for terminal output.
    """

    def __init__(self, root_node: DOMElement):
        self.root_node = root_node
        self._current_fiber: Optional[Any] = None
        self._host_context_stack: List[Dict[str, Any]] = [{"is_inside_text": False}]
        self._owner_component_stack: list[dict[str, Any]] = []
        self._error_boundary_stack: List[tuple[str, type[_Component], _Component]] = []
        self._suspense_boundary_stack: list[str] = []
        self._class_component_instances: Dict[str, _Component] = {}
        self._visited_class_component_ids: set[str] = set()
        self._pending_class_component_commit_callbacks: list[tuple[_Component, Callable[[], None]]] = []
        self._pending_component_did_catch: list[tuple[_Component, Exception]] = []
        self._deferred_component_did_catch: list[tuple[_Component, Exception]] = []
        self._commit_phase_recovery_requested = False
        self._devtools_container: Optional[ReconcilerContainer] = None
        self._devtools_forced_error_boundaries: set[str] = set()
        self._devtools_forced_error_boundary_states: dict[str, dict[str, Any]] = {}
        self._devtools_forced_suspense_boundaries: set[str] = set()
        self._devtools_nearest_error_boundary_by_node: dict[str, str] = {}
        self._devtools_nearest_suspense_boundary_by_node: dict[str, str] = {}
        self._devtools_prop_overrides: dict[str, dict[str, Any]] = {}
        self._devtools_effective_props: dict[str, dict[str, Any]] = {}
        self._next_devtools_effective_props: Optional[dict[str, dict[str, Any]]] = None
        self._devtools_inspected_elements: dict[str, dict[str, Any]] = {}
        self._next_devtools_inspected_elements: Optional[dict[str, dict[str, Any]]] = None
        self._devtools_inspected_element_fingerprints: dict[str, str] = {}
        self._next_devtools_inspected_element_fingerprints: Optional[dict[str, str]] = None
        self._devtools_most_recently_inspected_id: Optional[str] = None
        self._devtools_has_element_updated_since_last_inspected = False
        self._devtools_currently_inspected_paths: dict[str, Any] = {}
        self._devtools_last_copied_value: Optional[str] = None
        self._devtools_last_logged_element: Optional[dict[str, Any]] = None
        self._devtools_stored_globals: dict[str, Any] = {}
        self._devtools_backend_notification_log: list[dict[str, Any]] = []
        self._devtools_host_instance_ids: dict[int, str] = {}
        self._next_devtools_host_instance_ids: Optional[dict[int, str]] = None
        self._devtools_tracked_path: Optional[list[dict[str, Any]]] = None
        self._devtools_tree_snapshot: dict[str, Any] = {
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
        self._next_devtools_tree_snapshot: Optional[dict[str, Any]] = None
        self._host_config: Optional[ReconcilerHostConfig] = None
        self._on_commit: Optional[Callable[[], None]] = None
        self._on_immediate_commit: Optional[Callable[[], None]] = None

    def create_container(
        self,
        container: DOMElement,
        tag: int = 0,
        hydrate: bool = False,
    ) -> ReconcilerContainer:
        """
        Create a container for rendering.

        Args:
            container: The root DOM element.
            tag: Legacy (0) or Concurrent (1) mode.
            hydrate: Whether to hydrate existing content.

        Returns:
            The container (fiber root).
        """
        reconciler_container = ReconcilerContainer(container=container, tag=tag, hydrate=hydrate)
        if self._devtools_container is None:
            self._devtools_container = reconciler_container
        return reconciler_container

    def set_commit_handlers(
        self,
        *,
        on_commit: Optional[Callable[[], None]] = None,
        on_immediate_commit: Optional[Callable[[], None]] = None,
    ) -> None:
        self._on_commit = on_commit
        self._on_immediate_commit = on_immediate_commit

    def configure_host(
        self,
        host_config: Optional[ReconcilerHostConfig],
    ) -> None:
        self._host_config = host_config

    def injectIntoDevTools(self) -> bool:
        """Compatibility surface mirroring the upstream reconciler object."""
        from pyinkcli.devtools import createDevtoolsBackendFacade, initializeDevtools
        from pyinkcli.devtools_window_polyfill import installDevtoolsWindowPolyfill

        if not initializeDevtools():
            return False

        global_scope = installDevtoolsWindowPolyfill()
        renderer_interface = {
            "bundleType": 1,
            "version": packageInfo["version"],
            "rendererPackageName": packageInfo["name"],
            "reconcilerVersion": packageInfo["version"],
            "rendererID": id(self),
            "rendererConfig": {
                "supportsClassComponents": True,
                "supportsErrorBoundaries": True,
                "supportsCommitPhaseErrorRecovery": True,
            },
            "supportsTogglingSuspense": True,
            "getDisplayNameForNode": self.getDevtoolsDisplayName,
            "getDisplayNameForElementID": self.getDevtoolsDisplayName,
            "getTreeSnapshot": self.getDevtoolsTreeSnapshot,
            "getRootID": lambda: self._devtools_tree_snapshot["rootID"],
            "inspectElement": self.inspectDevtoolsElement,
            "inspectScreen": self.inspectDevtoolsScreen,
            "getSerializedElementValueByPath": self.getSerializedDevtoolsElementValueByPath,
            "getElementValueByPath": self.getDevtoolsElementValueByPath,
            "getElementAttributeByPath": self.getDevtoolsElementAttributeByPath,
            "getProfilingData": self.getDevtoolsProfilingData,
            "getPathForElement": self.getDevtoolsPathForElement,
            "getOwnersList": self.getDevtoolsOwnersList,
            "getElementIDForHostInstance": self.getDevtoolsElementIDForHostInstance,
            "getSuspenseNodeIDForHostInstance": self.getDevtoolsSuspenseNodeIDForHostInstance,
            "overrideError": self.overrideDevtoolsError,
            "overrideSuspense": self.overrideDevtoolsSuspense,
            "overrideSuspenseMilestone": self.overrideDevtoolsSuspenseMilestone,
            "overrideProps": self.overrideDevtoolsProps,
            "overridePropsDeletePath": self.deleteDevtoolsPropsPath,
            "overridePropsRenamePath": self.renameDevtoolsPropsPath,
            "overrideHookState": self.overrideDevtoolsHookState,
            "overrideHookStateDeletePath": self.deleteDevtoolsHookStatePath,
            "overrideHookStateRenamePath": self.renameDevtoolsHookStatePath,
            "overrideValueAtPath": self.overrideDevtoolsValueAtPath,
            "deletePath": self.deleteDevtoolsPath,
            "renamePath": self.renameDevtoolsPath,
            "scheduleUpdate": self.scheduleDevtoolsUpdate,
            "scheduleRetry": self.scheduleDevtoolsRetry,
            "clearErrorsAndWarnings": self.clearDevtoolsErrorsAndWarnings,
            "clearErrorsForElementID": self.clearDevtoolsErrorsForElement,
            "clearWarningsForElementID": self.clearDevtoolsWarningsForElement,
            "copyElementPath": self.copyDevtoolsElementPath,
            "storeAsGlobal": self.storeDevtoolsValueAsGlobal,
            "getLastCopiedValue": self.getDevtoolsLastCopiedValue,
            "getLastLoggedElement": self.getDevtoolsLastLoggedElement,
            "getTrackedPath": self.getDevtoolsTrackedPath,
            "getStoredGlobals": self.getDevtoolsStoredGlobals,
            "getBackendNotificationLog": self.getDevtoolsBackendNotificationLog,
            "logElementToConsole": self.logDevtoolsElementToConsole,
            "setTrackedPath": self.setDevtoolsTrackedPath,
        }
        renderer_interface["backendFacade"] = createDevtoolsBackendFacade(renderer_interface)
        renderer_interface["dispatchBridgeMessage"] = renderer_interface["backendFacade"]["dispatchMessage"]
        global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"] = renderer_interface
        global_scope["__INK_DEVTOOLS_RENDERERS__"][id(self)] = renderer_interface
        return True

    def getDevtoolsTreeSnapshot(self) -> dict[str, Any]:
        nodes = [
            dict(node)
            for node in self._devtools_tree_snapshot.get("nodes", [])
        ]
        return {
            "rootID": self._devtools_tree_snapshot.get("rootID", "root"),
            "nodes": nodes,
        }

    def getDevtoolsDisplayName(self, node_id: str) -> Optional[str]:
        for node in self._devtools_tree_snapshot.get("nodes", []):
            if node.get("id") == node_id:
                return node.get("displayName")
        return None

    def inspectDevtoolsElement(
        self,
        request_id: int,
        node_id: str,
        inspected_paths: Optional[Any] = None,
        force_full_data: bool = False,
    ) -> dict[str, Any]:
        path: Optional[list[Any]] = None
        if isinstance(inspected_paths, list):
            path = list(inspected_paths)

        if self._is_most_recently_inspected_element(node_id) and not force_full_data:
            if path is not None:
                self._merge_devtools_inspected_path(path)
            if not self._devtools_has_element_updated_since_last_inspected:
                if path is not None:
                    element = self._devtools_inspected_elements.get(node_id)
                    if element is None:
                        return {
                            "id": node_id,
                            "responseID": request_id,
                            "type": "not-found",
                        }
                    value, found = self._get_nested_value(element, path)
                    root_key = path[0] if path else None
                    if found and isinstance(root_key, str):
                        value = self._clean_devtools_value_for_bridge(
                            value,
                            root_key=root_key,
                            path=path,
                        )
                    return {
                        "id": node_id,
                        "responseID": request_id,
                        "type": "hydrated-path",
                        "path": path,
                        "value": value if found else None,
                    }
                return {
                    "id": node_id,
                    "responseID": request_id,
                    "type": "no-change",
                }
        else:
            self._devtools_currently_inspected_paths = {}

        if path is not None:
            self._merge_devtools_inspected_path(path)

        element = self._devtools_inspected_elements.get(node_id)
        if element is None:
            return {
                "id": node_id,
                "responseID": request_id,
                "type": "not-found",
            }
        self._devtools_most_recently_inspected_id = node_id
        self._devtools_has_element_updated_since_last_inspected = False
        return {
            "id": node_id,
            "responseID": request_id,
            "type": "full-data",
            "value": self._clean_devtools_inspected_element_for_bridge(element),
        }

    def inspectDevtoolsScreen(
        self,
        request_id: int,
        node_id: Optional[str] = None,
        path: Optional[Any] = None,
        force_full_data: bool = False,
        renderer_id: Optional[int] = None,
    ) -> dict[str, Any]:
        del renderer_id
        screen_id = node_id or self._devtools_tree_snapshot.get("rootID", "root")
        return self.inspectDevtoolsElement(
            request_id,
            screen_id,
            inspected_paths=path,
            force_full_data=force_full_data,
        )

    def getSerializedDevtoolsElementValueByPath(
        self,
        node_id: str,
        path: list[Any],
    ) -> Optional[str]:
        element = self._devtools_inspected_elements.get(node_id)
        if element is None:
            return None
        value, found = self._get_nested_value(element, path)
        if not found:
            return None
        try:
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        except TypeError:
            return repr(value)

    def getDevtoolsElementValueByPath(
        self,
        node_id: str,
        path: list[Any],
    ) -> Any:
        element = self._devtools_inspected_elements.get(node_id)
        if element is None:
            return None
        value, found = self._get_nested_value(element, path)
        if not found:
            return None
        return self._clone_devtools_value(value)

    def getDevtoolsElementAttributeByPath(
        self,
        node_id: str,
        path: list[Any],
    ) -> Any:
        return self.getDevtoolsElementValueByPath(node_id, path)

    def getDevtoolsProfilingData(self) -> dict[str, Any]:
        return {
            "dataForRoots": [
                {
                    "rootID": self._devtools_tree_snapshot.get("rootID", "root"),
                    "displayName": "Root",
                    "commitData": [],
                    "initialTreeBaseDurations": [],
                }
            ],
            "rendererID": id(self),
            "timelineData": None,
        }

    def getDevtoolsPathForElement(
        self,
        node_id: str,
    ) -> Optional[list[dict[str, Any]]]:
        nodes = self._devtools_tree_snapshot.get("nodes", [])
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
                (position for position, node in enumerate(siblings) if node.get("id") == current.get("id")),
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
        self,
        node_id: str,
    ) -> list[dict[str, Any]]:
        element = self._devtools_inspected_elements.get(node_id)
        if element is None:
            return []
        owners = element.get("owners")
        if not isinstance(owners, list):
            return []
        return self._clone_devtools_value(owners)

    def getDevtoolsElementIDForHostInstance(
        self,
        target: Any,
    ) -> Optional[str]:
        return self._devtools_host_instance_ids.get(id(target))

    def getDevtoolsSuspenseNodeIDForHostInstance(
        self,
        target: Any,
    ) -> Optional[str]:
        node_id = self.getDevtoolsElementIDForHostInstance(target)
        if node_id is None:
            return None
        return self._devtools_nearest_suspense_boundary_by_node.get(node_id)

    def overrideDevtoolsProps(
        self,
        node_id: str,
        path: list[Any],
        value: Any,
    ) -> bool:
        props = self._get_devtools_mutable_props(node_id)
        if props is None:
            return False
        self._set_nested_value(props, path, value)
        self._devtools_prop_overrides[node_id] = props
        return True

    def overrideDevtoolsError(self, node_id: str, force_error: bool) -> bool:
        boundary_id = self._devtools_nearest_error_boundary_by_node.get(node_id)
        if boundary_id is None:
            boundary_id = self._find_nearest_devtools_ancestor(
                node_id,
                predicate=lambda node: bool(node.get("isErrorBoundary")),
            )
        if boundary_id is None:
            return False

        instance = self._class_component_instances.get(boundary_id)
        if instance is None:
            return False

        if force_error:
            if boundary_id not in self._devtools_forced_error_boundaries:
                self._devtools_forced_error_boundary_states[boundary_id] = self._clone_devtools_value(
                    instance.state
                )
            self._devtools_forced_error_boundaries.add(boundary_id)
            self._apply_error_boundary_state(type(instance), instance, _DevtoolsForcedError("DevTools forced error"))
            return self.scheduleDevtoolsUpdate(boundary_id)

        self._devtools_forced_error_boundaries.discard(boundary_id)
        previous_state = self._devtools_forced_error_boundary_states.pop(boundary_id, None)
        if previous_state is not None:
            if instance._pending_previous_state is None:
                instance._pending_previous_state = dict(instance.state)
            instance.state = self._clone_devtools_value(previous_state)
            instance._state_version += 1
        return self.scheduleDevtoolsRetry(boundary_id)

    def overrideDevtoolsSuspense(self, node_id: str, force_fallback: bool) -> bool:
        suspense_id = self._devtools_nearest_suspense_boundary_by_node.get(node_id)
        if suspense_id is None:
            suspense_id = self._find_nearest_devtools_ancestor(
                node_id,
                predicate=lambda node: node.get("elementType") == "suspense",
            )
        if suspense_id is None:
            return False

        if force_fallback:
            self._devtools_forced_suspense_boundaries.add(suspense_id)
            return self.scheduleDevtoolsUpdate(suspense_id)

        self._devtools_forced_suspense_boundaries.discard(suspense_id)
        return self.scheduleDevtoolsRetry(suspense_id)

    def overrideDevtoolsSuspenseMilestone(
        self,
        suspended_set: list[str],
        renderer_id: Optional[int] = None,
    ) -> bool:
        normalized_target: set[str] = set()
        for node_id in suspended_set:
            suspense_id = self._devtools_nearest_suspense_boundary_by_node.get(node_id)
            if suspense_id is None:
                node = self._get_devtools_node(node_id)
                if node is not None and node.get("elementType") == "suspense":
                    suspense_id = node_id
                else:
                    suspense_id = self._find_nearest_devtools_ancestor(
                        node_id,
                        predicate=lambda candidate: candidate.get("elementType") == "suspense",
                    )
            if suspense_id is not None:
                normalized_target.add(suspense_id)

        current_forced = set(self._devtools_forced_suspense_boundaries)
        unsuspended = current_forced - normalized_target
        resuspended = False

        for suspense_id in normalized_target:
            if suspense_id in current_forced:
                unsuspended.discard(suspense_id)
                continue
            self._devtools_forced_suspense_boundaries.add(suspense_id)
            self.scheduleDevtoolsUpdate(suspense_id)
            resuspended = True

        for suspense_id in unsuspended:
            self._devtools_forced_suspense_boundaries.discard(suspense_id)
            if not resuspended:
                self.scheduleDevtoolsRetry(suspense_id)
            else:
                self.scheduleDevtoolsUpdate(suspense_id)

        self._record_devtools_backend_notification(
            "overrideSuspenseMilestone",
            renderer_id=renderer_id,
            suspended_set=list(suspended_set),
            normalized_suspended_set=sorted(normalized_target),
        )
        return True

    def deleteDevtoolsPropsPath(
        self,
        node_id: str,
        path: list[Any],
    ) -> bool:
        props = self._get_devtools_mutable_props(node_id)
        if props is None:
            return False
        if not self._delete_nested_value(props, path):
            return False
        self._devtools_prop_overrides[node_id] = props
        return True

    def renameDevtoolsPropsPath(
        self,
        node_id: str,
        old_path: list[Any],
        new_path: list[Any],
    ) -> bool:
        props = self._get_devtools_mutable_props(node_id)
        if props is None:
            return False
        value, found = self._pop_nested_value(props, old_path)
        if not found:
            return False
        self._set_nested_value(props, new_path, value)
        self._devtools_prop_overrides[node_id] = props
        return True

    def overrideDevtoolsValueAtPath(
        self,
        value_type: str,
        node_id: str,
        hook_id: Optional[int],
        path: list[Any],
        value: Any,
    ) -> bool:
        if value_type == "props":
            return self.overrideDevtoolsProps(node_id, path, value)
        if value_type == "hooks":
            hook_path = self._normalize_hook_edit_path(hook_id, path)
            if hook_path is None:
                return False
            return self.overrideDevtoolsHookState(node_id, hook_path, value)
        if value_type == "state":
            return self.overrideDevtoolsState(node_id, path, value)
        return False

    def deleteDevtoolsPath(
        self,
        value_type: str,
        node_id: str,
        hook_id: Optional[int],
        path: list[Any],
    ) -> bool:
        if value_type == "props":
            return self.deleteDevtoolsPropsPath(node_id, path)
        if value_type == "hooks":
            hook_path = self._normalize_hook_edit_path(hook_id, path)
            if hook_path is None:
                return False
            return self.deleteDevtoolsHookStatePath(node_id, hook_path)
        if value_type == "state":
            return self.deleteDevtoolsStatePath(node_id, path)
        return False

    def renameDevtoolsPath(
        self,
        value_type: str,
        node_id: str,
        hook_id: Optional[int],
        old_path: list[Any],
        new_path: list[Any],
    ) -> bool:
        if value_type == "props":
            return self.renameDevtoolsPropsPath(node_id, old_path, new_path)
        if value_type == "hooks":
            hook_old_path = self._normalize_hook_edit_path(hook_id, old_path)
            hook_new_path = self._normalize_hook_edit_path(hook_id, new_path)
            if hook_old_path is None or hook_new_path is None:
                return False
            return self.renameDevtoolsHookStatePath(node_id, hook_old_path, hook_new_path)
        if value_type == "state":
            return self.renameDevtoolsStatePath(node_id, old_path, new_path)
        return False

    def scheduleDevtoolsUpdate(self, node_id: str) -> bool:
        if not self._has_devtools_node(node_id):
            return False
        if self._devtools_container is None:
            return False
        self.request_rerender(self._devtools_container, priority="default")
        return True

    def scheduleDevtoolsRetry(self, node_id: str) -> bool:
        if not self._has_devtools_node(node_id):
            return False
        if self._devtools_container is None:
            return False
        self.request_rerender(self._devtools_container, priority="default")
        return True

    def clearDevtoolsErrorsAndWarnings(
        self,
        renderer_id: Optional[int] = None,
    ) -> bool:
        self._record_devtools_backend_notification(
            "clearErrorsAndWarnings",
            renderer_id=renderer_id,
        )
        return True

    def clearDevtoolsErrorsForElement(
        self,
        id: str,
        renderer_id: Optional[int] = None,
    ) -> bool:
        self._record_devtools_backend_notification(
            "clearErrorsForElementID",
            renderer_id=renderer_id,
            node_id=id,
        )
        return self._has_devtools_node(id)

    def clearDevtoolsWarningsForElement(
        self,
        id: str,
        renderer_id: Optional[int] = None,
    ) -> bool:
        self._record_devtools_backend_notification(
            "clearWarningsForElementID",
            renderer_id=renderer_id,
            node_id=id,
        )
        return self._has_devtools_node(id)

    def copyDevtoolsElementPath(
        self,
        id: str,
        path: list[Any],
        renderer_id: Optional[int] = None,
    ) -> Optional[str]:
        from pyinkcli.devtools_window_polyfill import installDevtoolsWindowPolyfill

        copied = self.getSerializedDevtoolsElementValueByPath(id, path)
        self._devtools_last_copied_value = copied
        self._record_devtools_backend_notification(
            "copyElementPath",
            renderer_id=renderer_id,
            node_id=id,
            path=path,
            copied_value=copied,
        )
        installDevtoolsWindowPolyfill()["__INK_DEVTOOLS_LAST_COPIED_VALUE__"] = copied
        return copied

    def storeDevtoolsValueAsGlobal(
        self,
        id: str,
        path: list[Any],
        count: int,
        renderer_id: Optional[int] = None,
    ) -> Optional[str]:
        from pyinkcli.devtools_window_polyfill import installDevtoolsWindowPolyfill

        global_key = f"$reactTemp{count}"
        value = self.getDevtoolsElementValueByPath(id, path)
        self._devtools_stored_globals[global_key] = value
        self._record_devtools_backend_notification(
            "storeAsGlobal",
            renderer_id=renderer_id,
            node_id=id,
            path=path,
            count=count,
            global_key=global_key,
        )
        global_scope = installDevtoolsWindowPolyfill()
        global_scope.setdefault("__INK_DEVTOOLS_STORED_GLOBALS__", {})[global_key] = value
        global_scope[global_key] = value
        return global_key

    def getDevtoolsLastCopiedValue(self) -> Optional[str]:
        return self._devtools_last_copied_value

    def getDevtoolsLastLoggedElement(self) -> Optional[dict[str, Any]]:
        if self._devtools_last_logged_element is None:
            return None
        return self._clone_devtools_value(self._devtools_last_logged_element)

    def getDevtoolsTrackedPath(self) -> Optional[list[dict[str, Any]]]:
        if self._devtools_tracked_path is None:
            return None
        return self._clone_devtools_value(self._devtools_tracked_path)

    def getDevtoolsStoredGlobals(self) -> dict[str, Any]:
        return self._clone_devtools_value(self._devtools_stored_globals)

    def getDevtoolsBackendNotificationLog(self) -> list[dict[str, Any]]:
        return [
            {
                key: self._clone_devtools_value(value)
                for key, value in entry.items()
            }
            for entry in self._devtools_backend_notification_log
        ]

    def logDevtoolsElementToConsole(
        self,
        id: str,
        renderer_id: Optional[int] = None,
    ) -> bool:
        from pyinkcli.devtools_window_polyfill import installDevtoolsWindowPolyfill

        element = self._devtools_inspected_elements.get(id)
        if element is None:
            return False
        snapshot = self._clone_devtools_value(element)
        self._devtools_last_logged_element = snapshot
        self._record_devtools_backend_notification(
            "logElementToConsole",
            renderer_id=renderer_id,
            node_id=id,
        )
        installDevtoolsWindowPolyfill()["__INK_DEVTOOLS_LAST_LOGGED_ELEMENT__"] = snapshot
        return True

    def setDevtoolsTrackedPath(
        self,
        path: Optional[list[dict[str, Any]]],
    ) -> None:
        self._devtools_tracked_path = self._clone_devtools_value(path) if path is not None else None

    def overrideDevtoolsHookState(
        self,
        node_id: str,
        path: list[Any],
        value: Any,
    ) -> bool:
        return _override_hook_state(node_id, path, value)

    def deleteDevtoolsHookStatePath(
        self,
        node_id: str,
        path: list[Any],
    ) -> bool:
        return _delete_hook_state_path(node_id, path)

    def renameDevtoolsHookStatePath(
        self,
        node_id: str,
        old_path: list[Any],
        new_path: list[Any],
    ) -> bool:
        return _rename_hook_state_path(node_id, old_path, new_path)

    def overrideDevtoolsState(
        self,
        node_id: str,
        path: list[Any],
        value: Any,
    ) -> bool:
        instance = self._class_component_instances.get(node_id)
        if instance is None:
            return False
        if not path:
            if not isinstance(value, dict):
                return False
            if instance._pending_previous_state is None:
                instance._pending_previous_state = dict(instance.state)
            instance.state = self._clone_devtools_value(value)
            return True
        if instance._pending_previous_state is None:
            instance._pending_previous_state = dict(instance.state)
        return self._set_nested_value(instance.state, path, value)

    def deleteDevtoolsStatePath(
        self,
        node_id: str,
        path: list[Any],
    ) -> bool:
        instance = self._class_component_instances.get(node_id)
        if instance is None or not path:
            return False
        if instance._pending_previous_state is None:
            instance._pending_previous_state = dict(instance.state)
        return self._delete_nested_value(instance.state, path)

    def renameDevtoolsStatePath(
        self,
        node_id: str,
        old_path: list[Any],
        new_path: list[Any],
    ) -> bool:
        instance = self._class_component_instances.get(node_id)
        if instance is None or not old_path or not new_path:
            return False
        if instance._pending_previous_state is None:
            instance._pending_previous_state = dict(instance.state)
        value, found = self._pop_nested_value(instance.state, old_path)
        if not found:
            return False
        return self._set_nested_value(instance.state, new_path, value)

    def _get_devtools_mutable_props(self, node_id: str) -> Optional[dict[str, Any]]:
        base = self._devtools_prop_overrides.get(node_id)
        if base is None:
            base = self._devtools_effective_props.get(node_id)
        if base is None:
            return None
        return self._clone_devtools_value(base)

    def _record_devtools_backend_notification(
        self,
        event: str,
        *,
        renderer_id: Optional[int] = None,
        node_id: Optional[str] = None,
        path: Optional[list[Any]] = None,
        count: Optional[int] = None,
        copied_value: Optional[str] = None,
        global_key: Optional[str] = None,
        suspended_set: Optional[list[Any]] = None,
        normalized_suspended_set: Optional[list[Any]] = None,
    ) -> None:
        entry: dict[str, Any] = {"event": event}
        if renderer_id is not None:
            entry["rendererID"] = renderer_id
        if node_id is not None:
            entry["id"] = node_id
        if path is not None:
            entry["path"] = list(path)
        if count is not None:
            entry["count"] = count
        if copied_value is not None:
            entry["copiedValue"] = copied_value
        if global_key is not None:
            entry["globalKey"] = global_key
        if suspended_set is not None:
            entry["suspendedSet"] = self._clone_devtools_value(suspended_set)
        if normalized_suspended_set is not None:
            entry["normalizedSuspendedSet"] = self._clone_devtools_value(normalized_suspended_set)
        self._devtools_backend_notification_log.append(entry)

    def _has_devtools_node(self, node_id: str) -> bool:
        return any(
            node.get("id") == node_id
            for node in self._devtools_tree_snapshot.get("nodes", [])
        )

    def _is_most_recently_inspected_element(self, node_id: str) -> bool:
        return self._devtools_most_recently_inspected_id == node_id

    def _merge_devtools_inspected_path(self, path: list[Any]) -> None:
        current = self._devtools_currently_inspected_paths
        for key in path:
            current = current.setdefault(key, {})

    def _get_devtools_node(self, node_id: str) -> Optional[dict[str, Any]]:
        for node in self._devtools_tree_snapshot.get("nodes", []):
            if node.get("id") == node_id:
                return node
        return None

    def _find_nearest_devtools_ancestor(
        self,
        node_id: str,
        *,
        predicate: Callable[[dict[str, Any]], bool],
    ) -> Optional[str]:
        current_id: Optional[str] = node_id
        while current_id is not None:
            node = self._get_devtools_node(current_id)
            if node is None:
                return None
            if predicate(node):
                return current_id
            current_id = node.get("parentID")
        return None

    def _normalize_hook_edit_path(
        self,
        hook_id: Optional[int],
        path: list[Any],
    ) -> Optional[list[Any]]:
        if hook_id is None:
            return list(path) if path else None
        return [hook_id, *path]

    def _clone_devtools_value(self, value: Any) -> Any:
        if type(value) is dict:
            return {
                key: self._clone_devtools_value(item)
                for key, item in value.items()
            }
        if isinstance(value, dict):
            try:
                return type(value)(
                    (key, self._clone_devtools_value(item))
                    for key, item in value.items()
                )
            except Exception:
                return {
                    key: self._clone_devtools_value(item)
                    for key, item in value.items()
                }
        if isinstance(value, list):
            return [self._clone_devtools_value(item) for item in value]
        return value

    def _fingerprint_devtools_value(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {
                str(key): self._fingerprint_devtools_value(item)
                for key, item in sorted(value.items(), key=lambda entry: str(entry[0]))
            }
        if isinstance(value, list):
            return [self._fingerprint_devtools_value(item) for item in value]
        if isElement(value):
            element_type = getattr(value, "type", None)
            if callable(element_type):
                display_name = self._get_component_display_name(element_type)
            else:
                display_name = str(element_type)
            return {
                "__element__": display_name,
                "key": getattr(value, "key", None),
                "childrenCount": len(getattr(value, "children", ()) or ()),
            }
        if isinstance(value, BaseException):
            return {
                "__error__": type(value).__name__,
                "message": str(value),
            }
        if callable(value):
            return {"__callable__": getattr(value, "__name__", repr(value))}
        return repr(value)

    def _build_devtools_fingerprint(self, value: Any) -> str:
        return json.dumps(
            self._fingerprint_devtools_value(value),
            ensure_ascii=False,
            sort_keys=True,
        )

    def _get_devtools_data_type(self, value: Any) -> str:
        if value is None:
            return "null"
        if getattr(value, "__ink_devtools_react_lazy__", False):
            return "react_lazy"
        if getattr(value, "__ink_devtools_html_element__", False):
            return "html_element"
        if getattr(value, "__ink_devtools_html_all_collection__", False):
            return "html_all_collection"
        if getattr(value, "__ink_devtools_bigint__", False):
            return "bigint"
        if getattr(value, "__ink_devtools_unknown__", False):
            return "unknown"
        if isinstance(value, enum.Enum):
            return "symbol"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, str):
            return "string"
        if isinstance(value, int):
            return "number"
        if isinstance(value, float):
            if value == float("inf") or value == float("-inf"):
                return "infinity"
            if value != value:
                return "nan"
            return "number"
        if isinstance(
            value,
            (
                datetime_module.date,
                datetime_module.datetime,
                datetime_module.time,
            ),
        ):
            return "date"
        if isinstance(value, re.Pattern):
            return "regexp"
        if isinstance(value, (bytes, bytearray)):
            return "array_buffer"
        if isinstance(value, memoryview):
            return "data_view"
        if isinstance(value, array_module.array):
            return "typed_array"
        if isinstance(value, (asyncio.Future, concurrent.futures.Future)):
            return "thenable"
        if hasattr(value, "then") and callable(getattr(value, "then")):
            return "thenable"
        if isinstance(value, collections_abc.Iterator):
            return "opaque_iterator"
        if isinstance(
            value,
            (
                set,
                frozenset,
                collections_abc.ItemsView,
                collections_abc.KeysView,
                collections_abc.ValuesView,
            ),
        ):
            return "iterator"
        if isinstance(value, collections_abc.Mapping) and type(value) is not dict:
            return "iterator"
        if isinstance(value, dict):
            return "object"
        if isinstance(value, list):
            return "array"
        if isElement(value):
            return "react_element"
        if isinstance(value, BaseException):
            return "error"
        if callable(value):
            return "function"
        if hasattr(value, "__dict__"):
            return "class_instance"
        return "object"

    def _preview_devtools_value(self, value: Any, *, short: bool) -> str:
        data_type = self._get_devtools_data_type(value)
        if data_type == "react_lazy":
            payload = getattr(value, "_payload", None)
            status = self._get_devtools_lazy_status(payload)
            if status == "fulfilled":
                resolved = self._get_devtools_lazy_resolved_value(payload)
                if short:
                    return "fulfilled lazy() {…}"
                if resolved is not None:
                    return f"fulfilled lazy() {{{self._preview_devtools_value(resolved, short=True)}}}"
                return "fulfilled lazy() {…}"
            if status == "rejected":
                reason = self._get_devtools_lazy_rejected_value(payload)
                if short:
                    return "rejected lazy() {…}"
                if reason is not None:
                    return f"rejected lazy() {{{self._preview_devtools_value(reason, short=True)}}}"
                return "rejected lazy() {…}"
            return "pending lazy()" if status == "pending" else "lazy()"
        if data_type == "html_element":
            tag_name = getattr(value, "tagName", "div")
            preview = f"<{str(tag_name).lower()} />"
            return preview if len(preview) <= 50 else preview[:50] + "..."
        if data_type == "bigint":
            preview = f"{getattr(value, 'value', value)}n"
            return preview if len(preview) <= 50 else preview[:50] + "..."
        if data_type == "unknown":
            preview = getattr(value, "__ink_devtools_unknown_preview__", "")
            if short:
                return "[Exception]"
            return f"[Exception: {preview}]" if preview else "[Exception]"
        if data_type == "string":
            preview = json.dumps(value, ensure_ascii=False)
            if len(preview) > 50:
                preview = preview[:50] + "..."
            return preview
        if data_type == "date":
            preview = str(value)
            return preview if len(preview) <= 50 else preview[:50] + "..."
        if data_type == "regexp":
            preview = repr(value)
            return preview if len(preview) <= 50 else preview[:50] + "..."
        if data_type == "symbol":
            preview = str(value)
            return preview if len(preview) <= 50 else preview[:50] + "..."
        if data_type == "html_all_collection":
            preview = str(value)
            return preview if len(preview) <= 50 else preview[:50] + "..."
        if data_type == "array_buffer":
            size = self._get_devtools_buffer_size(value)
            return f"ArrayBuffer({size})"
        if data_type == "data_view":
            size = self._get_devtools_buffer_size(value)
            return f"DataView({size})"
        if data_type == "object":
            if short:
                return "{…}"
            parts: list[str] = []
            for key, item in list(value.items())[:4]:
                parts.append(f"{key}: {self._preview_devtools_value(item, short=True)}")
            preview = ", ".join(parts)
            if len(value) > 4:
                preview += ", ..."
            if len(preview) > 50:
                preview = preview[:50] + "..."
            return "{" + preview + "}"
        if data_type == "array":
            if short:
                return f"Array({len(value)})"
            preview = ", ".join(
                self._preview_devtools_value(item, short=True)
                for item in value[:4]
            )
            if len(value) > 4:
                preview += ", ..."
            if len(preview) > 50:
                preview = preview[:50] + "..."
            return "[" + preview + "]"
        if data_type == "react_element":
            element_type = getattr(value, "type", None)
            name = (
                self._get_component_display_name(element_type)
                if callable(element_type)
                else str(element_type)
            )
            return f"<{name} />"
        if data_type == "typed_array":
            name = self._get_devtools_name(value)
            size = len(value)
            if short:
                return f"{name}({size})"
            preview = ", ".join(str(item) for item in list(value)[:4])
            if len(value) > 4:
                preview += ", ..."
            if len(preview) > 50:
                preview = preview[:50] + "..."
            return f"{name}({size}) [{preview}]"
        if data_type == "class_instance":
            name = self._get_devtools_name(value)
            return name or repr(value)
        if data_type == "iterator":
            name = self._get_devtools_name(value) or "Iterator"
            size = self._get_devtools_iterator_size(value)
            if short:
                return f"{name}({size})" if size is not None else name
            items = self._get_devtools_iterator_items(value)
            parts: list[str] = []
            for item in items[:4]:
                if isinstance(item, list) and len(item) == 2:
                    parts.append(
                        f"{self._preview_devtools_value(item[0], short=True)} => {self._preview_devtools_value(item[1], short=True)}"
                    )
                else:
                    parts.append(self._preview_devtools_value(item, short=True))
            preview = ", ".join(parts)
            if len(items) > 4:
                preview += ", ..."
            if len(preview) > 50:
                preview = preview[:50] + "..."
            if size is not None:
                return f"{name}({size})" + " {" + preview + "}"
            return name + " {" + preview + "}"
        if data_type == "opaque_iterator":
            return self._get_devtools_name(value) or "Iterator"
        if data_type == "thenable":
            display_name = self._get_devtools_thenable_display_name(value)
            status = self._get_devtools_thenable_status(value)
            if status == "fulfilled":
                resolved = self._get_devtools_thenable_value(value)
                if short:
                    return f"fulfilled {display_name} {{…}}"
                if resolved is not None:
                    return f"fulfilled {display_name} {{{self._preview_devtools_value(resolved, short=True)}}}"
                return f"fulfilled {display_name} {{…}}"
            if status == "rejected":
                reason = self._get_devtools_thenable_reason(value)
                if short:
                    return f"rejected {display_name} {{…}}"
                if reason is not None:
                    return f"rejected {display_name} {{{self._preview_devtools_value(reason, short=True)}}}"
                return f"rejected {display_name} {{…}}"
            if status == "pending":
                return f"pending {display_name}"
            return display_name
        if data_type == "function":
            name = getattr(value, "__name__", "")
            return "() => {}" if not name or name == "<lambda>" else f"{name}() {{}}"
        if data_type == "error":
            preview = f"{type(value).__name__}: {value}"
            return preview if len(preview) <= 50 else preview[:50] + "..."
        return repr(value)

    def _get_devtools_name(self, value: Any) -> str:
        data_type = self._get_devtools_data_type(value)
        if data_type == "react_lazy":
            return "lazy()"
        if data_type == "html_element":
            return str(getattr(value, "tagName", "div"))
        if data_type == "bigint":
            return str(getattr(value, "value", value))
        if data_type == "unknown":
            return str(getattr(value, "__ink_devtools_unknown_preview__", ""))
        if data_type == "object":
            constructor = getattr(type(value), "__name__", "")
            return "" if constructor == "dict" else constructor
        if data_type == "array":
            return "Array"
        if data_type == "array_buffer":
            return "ArrayBuffer"
        if data_type == "data_view":
            return "DataView"
        if data_type == "typed_array":
            return getattr(type(value), "__name__", "TypedArray")
        if data_type in {"date", "regexp", "symbol"}:
            return str(value)
        if data_type in {"iterator", "opaque_iterator", "html_all_collection"}:
            constructor = getattr(type(value), "__name__", "")
            return constructor or "Iterator"
        if data_type == "react_element":
            element_type = getattr(value, "type", None)
            return (
                self._get_component_display_name(element_type)
                if callable(element_type)
                else str(element_type)
            )
        if data_type == "class_instance":
            constructor = getattr(type(value), "__name__", "")
            return constructor if constructor != "object" else ""
        if data_type == "function":
            return getattr(value, "__name__", "function")
        if data_type == "error":
            return type(value).__name__
        if data_type == "thenable":
            return self._get_devtools_thenable_display_name(value)
        return ""

    def _create_dehydrated_metadata(
        self,
        value: Any,
        *,
        inspectable: bool,
        unserializable: bool,
        inspected: bool = False,
    ) -> dict[str, Any]:
        data_type = self._get_devtools_data_type(value)
        metadata = {
            "inspected": inspected,
            "inspectable": inspectable,
            "name": self._get_devtools_name(value),
            "preview_short": self._preview_devtools_value(value, short=True),
            "preview_long": self._preview_devtools_value(value, short=False),
            "type": data_type,
        }
        if isinstance(value, (dict, list)):
            metadata["size"] = len(value)
        elif data_type in {"array_buffer", "data_view"}:
            metadata["size"] = self._get_devtools_buffer_size(value)
        elif data_type == "typed_array":
            metadata["size"] = len(value)
        elif data_type == "iterator":
            size = self._get_devtools_iterator_size(value)
            if size is not None:
                metadata["size"] = size
        elif data_type == "class_instance":
            metadata["size"] = len(vars(value))
        if data_type in {"react_element", "error", "class_instance", "iterator", "typed_array"}:
            metadata["readonly"] = True
        if unserializable:
            metadata["unserializable"] = True
        return metadata

    def _get_transport_element_children(self, element: Any) -> Any:
        children = list(getattr(element, "children", []) or [])
        if not children:
            return None
        if len(children) == 1:
            return children[0]
        return children

    def _get_devtools_enumerable_entries(self, value: Any) -> list[tuple[str, Any]]:
        if isinstance(value, dict):
            return [(str(key), item) for key, item in value.items()]
        try:
            return list(vars(value).items())
        except TypeError:
            return []

    def _get_devtools_buffer_size(self, value: Any) -> int:
        if isinstance(value, memoryview):
            return value.nbytes
        return len(value)

    def _get_devtools_iterator_items(self, value: Any) -> list[Any]:
        if isinstance(value, collections_abc.Mapping):
            return [[key, item] for key, item in value.items()]
        if isinstance(value, collections_abc.ItemsView):
            return [[key, item] for key, item in value]
        return list(value)

    def _get_devtools_iterator_size(self, value: Any) -> Optional[int]:
        try:
            return len(value)
        except TypeError:
            return None

    def _get_devtools_thenable_display_name(self, value: Any) -> str:
        constructor = getattr(type(value), "__name__", "")
        return constructor or "Thenable"

    def _get_devtools_thenable_status(self, value: Any) -> str:
        if isinstance(value, (asyncio.Future, concurrent.futures.Future)):
            if not value.done():
                return "pending"
            try:
                value.result()
            except BaseException:
                return "rejected"
            return "fulfilled"
        status = getattr(value, "status", None)
        return status if isinstance(status, str) else "pending"

    def _get_devtools_thenable_value(self, value: Any) -> Any:
        if isinstance(value, (asyncio.Future, concurrent.futures.Future)):
            return value.result()
        return getattr(value, "value", None)

    def _get_devtools_thenable_reason(self, value: Any) -> Any:
        if isinstance(value, (asyncio.Future, concurrent.futures.Future)):
            try:
                value.result()
            except BaseException as error:
                return error
            return None
        return getattr(value, "reason", None)

    def _get_devtools_lazy_status(self, payload: Any) -> Optional[str]:
        if payload is None:
            return None
        raw_status = getattr(payload, "_status", None)
        if raw_status == 0:
            return "pending"
        if raw_status == 1:
            return "fulfilled"
        if raw_status == 2:
            return "rejected"
        status = getattr(payload, "status", None)
        return status if isinstance(status, str) else None

    def _get_devtools_lazy_resolved_value(self, payload: Any) -> Any:
        if payload is None:
            return None
        if getattr(payload, "_status", None) == 1:
            result = getattr(payload, "_result", None)
            default = getattr(result, "default", None)
            return result if default is None else default
        return getattr(payload, "value", None)

    def _get_devtools_lazy_rejected_value(self, payload: Any) -> Any:
        if payload is None:
            return None
        if getattr(payload, "_status", None) == 2:
            return getattr(payload, "_result", None)
        return getattr(payload, "reason", None)

    def _create_unserializable_transport_value(
        self,
        value: Any,
        *,
        root_key: str,
        path: list[Any],
        lookup_path: list[Any],
        cleaned: list[list[Any]],
        unserializable: list[list[Any]],
    ) -> dict[str, Any]:
        data_type = self._get_devtools_data_type(value)
        metadata = self._create_dehydrated_metadata(
            value,
            inspectable=isElement(value)
            or isinstance(value, BaseException)
            or data_type in {"class_instance", "iterator"},
            unserializable=True,
        )
        data_type = metadata["type"]

        if data_type == "react_element":
            metadata["key"] = self._dehydrate_devtools_value_for_bridge(
                getattr(value, "key", None),
                root_key=root_key,
                path=[*path, "key"],
                lookup_path=[*lookup_path, "key"],
                cleaned=cleaned,
                unserializable=unserializable,
            )
            element_props = dict(getattr(value, "props", {}))
            children = self._get_transport_element_children(value)
            if children is not None:
                element_props["children"] = children
            metadata["props"] = self._dehydrate_devtools_value_for_bridge(
                element_props,
                root_key=root_key,
                path=[*path, "props"],
                lookup_path=[*lookup_path, "props"],
                cleaned=cleaned,
                unserializable=unserializable,
            )
        elif data_type == "error":
            metadata["message"] = self._dehydrate_devtools_value_for_bridge(
                str(value),
                root_key=root_key,
                path=[*path, "message"],
                lookup_path=[*lookup_path, "message"],
                cleaned=cleaned,
                unserializable=unserializable,
            )
            metadata["stack"] = self._dehydrate_devtools_value_for_bridge(
                self._get_devtools_error_stack(value),
                root_key=root_key,
                path=[*path, "stack"],
                lookup_path=[*lookup_path, "stack"],
                cleaned=cleaned,
                unserializable=unserializable,
            )
            cause = getattr(value, "__cause__", None)
            if cause is not None:
                metadata["cause"] = self._dehydrate_devtools_value_for_bridge(
                    cause,
                    root_key=root_key,
                    path=[*path, "cause"],
                    lookup_path=[*lookup_path, "cause"],
                    cleaned=cleaned,
                    unserializable=unserializable,
                )
            for key, item in self._get_devtools_enumerable_entries(value):
                if key in {"message", "stack", "cause"}:
                    continue
                metadata[key] = self._dehydrate_devtools_value_for_bridge(
                    item,
                    root_key=root_key,
                    path=[*path, key],
                    lookup_path=[*lookup_path, key],
                    cleaned=cleaned,
                    unserializable=unserializable,
                )
        elif data_type == "class_instance":
            for key, item in self._get_devtools_enumerable_entries(value):
                metadata[key] = self._dehydrate_devtools_value_for_bridge(
                    item,
                    root_key=root_key,
                    path=[*path, key],
                    lookup_path=[*lookup_path, key],
                    cleaned=cleaned,
                    unserializable=unserializable,
                )
        elif data_type == "typed_array":
            for index, item in enumerate(list(value)):
                metadata[index] = self._dehydrate_devtools_value_for_bridge(
                    item,
                    root_key=root_key,
                    path=[*path, index],
                    lookup_path=[root_key],
                    cleaned=cleaned,
                    unserializable=unserializable,
                )
        elif data_type == "html_all_collection":
            metadata["readonly"] = True
            for index, item in enumerate(self._get_devtools_iterator_items(value)):
                metadata[index] = self._dehydrate_devtools_value_for_bridge(
                    item,
                    root_key=root_key,
                    path=[*path, index],
                    lookup_path=[root_key],
                    cleaned=cleaned,
                    unserializable=unserializable,
                )
        elif data_type == "iterator":
            for index, item in enumerate(self._get_devtools_iterator_items(value)):
                metadata[index] = self._dehydrate_devtools_value_for_bridge(
                    item,
                    root_key=root_key,
                    path=[*path, index],
                    lookup_path=[root_key],
                    cleaned=cleaned,
                    unserializable=unserializable,
                )
        elif data_type == "thenable":
            status = self._get_devtools_thenable_status(value)
            metadata["name"] = (
                "fulfilled Thenable"
                if status == "fulfilled"
                else "rejected Thenable"
                if status == "rejected"
                else self._get_devtools_thenable_display_name(value)
            )
            if status == "fulfilled":
                metadata["value"] = self._dehydrate_devtools_value_for_bridge(
                    self._get_devtools_thenable_value(value),
                    root_key=root_key,
                    path=[*path, "value"],
                    lookup_path=[*lookup_path, "value"],
                    cleaned=cleaned,
                    unserializable=unserializable,
                )
            elif status == "rejected":
                metadata["reason"] = self._dehydrate_devtools_value_for_bridge(
                    self._get_devtools_thenable_reason(value),
                    root_key=root_key,
                    path=[*path, "reason"],
                    lookup_path=[*lookup_path, "reason"],
                    cleaned=cleaned,
                    unserializable=unserializable,
                )
        elif data_type == "react_lazy":
            metadata["_payload"] = self._dehydrate_devtools_value_for_bridge(
                getattr(value, "_payload", None),
                root_key=root_key,
                path=[*path, "_payload"],
                lookup_path=[*lookup_path, "_payload"],
                cleaned=cleaned,
                unserializable=unserializable,
            )

        return metadata

    def _is_devtools_path_inspected(self, path: list[Any]) -> bool:
        current: Any = self._devtools_currently_inspected_paths
        for key in path:
            if not isinstance(current, dict) or key not in current:
                return False
            current = current[key]
        return True

    def _should_expand_devtools_path(
        self,
        root_key: str,
        lookup_path: list[Any],
    ) -> bool:
        if len(lookup_path) <= 1:
            return True
        if root_key == "hooks":
            if len(lookup_path) == 2 and isinstance(lookup_path[1], int):
                return True
            if lookup_path[-1] == "subHooks":
                return True
            if len(lookup_path) >= 2 and lookup_path[-2] == "subHooks":
                return True
            if (
                len(lookup_path) >= 2
                and lookup_path[-2] == "hookSource"
                and lookup_path[-1] == "fileName"
            ):
                return True
        elif root_key == "suspendedBy":
            if len(lookup_path) < 5:
                return True
        return self._is_devtools_path_inspected(lookup_path)

    def _dehydrate_devtools_value_for_bridge(
        self,
        value: Any,
        *,
        root_key: str,
        path: list[Any],
        lookup_path: list[Any],
        cleaned: list[list[Any]],
        unserializable: list[list[Any]],
    ) -> Any:
        data_type = self._get_devtools_data_type(value)
        if data_type in {"infinity", "nan"}:
            cleaned.append(list(path))
            return {"type": data_type}

        if data_type in {"html_element", "date", "regexp", "symbol", "bigint", "unknown", "opaque_iterator", "array_buffer", "data_view"}:
            cleaned.append(list(path))
            return self._create_dehydrated_metadata(
                value,
                inspectable=False,
                unserializable=False,
            )

        if value is None or isinstance(value, (str, int, float, bool)):
            return self._clone_devtools_value(value)

        if data_type == "thenable":
            status = self._get_devtools_thenable_status(value)
            if status not in {"fulfilled", "rejected"}:
                cleaned.append(list(path))
                return self._create_dehydrated_metadata(
                    value,
                    inspectable=False,
                    unserializable=False,
                )

        if data_type in {"react_element", "function", "error", "class_instance", "iterator", "html_all_collection", "typed_array", "thenable", "react_lazy"}:
            unserializable.append(list(path))
            return self._create_unserializable_transport_value(
                value,
                root_key=root_key,
                path=path,
                lookup_path=lookup_path,
                cleaned=cleaned,
                unserializable=unserializable,
            )

        if not self._should_expand_devtools_path(root_key, lookup_path):
            cleaned.append(list(path))
            return self._create_dehydrated_metadata(
                value,
                inspectable=isinstance(value, (dict, list)) or data_type == "iterator",
                unserializable=False,
            )

        if isinstance(value, dict):
            return {
                key: self._dehydrate_devtools_value_for_bridge(
                    item,
                    root_key=root_key,
                    path=[*path, key],
                    lookup_path=[*lookup_path, key],
                    cleaned=cleaned,
                    unserializable=unserializable,
                )
                for key, item in value.items()
            }

        if isinstance(value, list):
            return [
                self._dehydrate_devtools_value_for_bridge(
                    item,
                    root_key=root_key,
                    path=[*path, index],
                    lookup_path=[*lookup_path, index],
                    cleaned=cleaned,
                    unserializable=unserializable,
                )
                for index, item in enumerate(value)
            ]

        cleaned.append(list(path))
        return self._create_dehydrated_metadata(
            value,
            inspectable=False,
            unserializable=False,
        )

    def _clean_devtools_value_for_bridge(
        self,
        value: Any,
        *,
        root_key: str,
        path: list[Any],
        lookup_path: Optional[list[Any]] = None,
    ) -> dict[str, Any]:
        cleaned: list[list[Any]] = []
        unserializable: list[list[Any]] = []
        effective_lookup_path = list(path) if lookup_path is None else list(lookup_path)
        data = self._dehydrate_devtools_value_for_bridge(
            value,
            root_key=root_key,
            path=path,
            lookup_path=effective_lookup_path,
            cleaned=cleaned,
            unserializable=unserializable,
        )
        return {
            "data": data,
            "cleaned": cleaned,
            "unserializable": unserializable,
        }

    def _clean_devtools_inspected_element_for_bridge(
        self,
        element: dict[str, Any],
    ) -> dict[str, Any]:
        cleaned = self._clone_devtools_value(element)
        for root_key in ("context", "hooks", "props", "state", "suspendedBy"):
            cleaned[root_key] = self._clean_devtools_value_for_bridge(
                element.get(root_key),
                root_key=root_key,
                path=[],
                lookup_path=[root_key],
            )
        return cleaned

    def _get_devtools_error_stack(self, value: BaseException) -> Optional[str]:
        stack = "".join(
            traceback.format_exception(
                type(value),
                value,
                value.__traceback__,
            )
        ).rstrip()
        return stack or None

    def _get_devtools_named_value(
        self,
        target: Any,
        key: Any,
    ) -> tuple[Any, bool]:
        if isinstance(key, int):
            if isinstance(target, array_module.array):
                if key >= len(target):
                    return (None, False)
                return (target[key], True)
            if isinstance(target, tuple):
                if key >= len(target):
                    return (None, False)
                return (target[key], True)
            if not isinstance(target, list) or key >= len(target):
                return (None, False)
            return (target[key], True)

        if isinstance(target, dict):
            if key not in target:
                return (None, False)
            return (target[key], True)

        if isinstance(target, BaseException):
            if key == "message":
                return (str(target), True)
            if key == "stack":
                return (self._get_devtools_error_stack(target), True)
            if key == "cause":
                cause = getattr(target, "__cause__", None)
                return (cause, cause is not None)
            entries = self._get_devtools_enumerable_entries(target)
            for entry_key, entry_value in entries:
                if entry_key == key:
                    return (entry_value, True)
            return (None, False)

        if hasattr(target, "__dict__"):
            entries = vars(target)
            if key in entries:
                return (entries[key], True)

        target_type = self._get_devtools_data_type(target)
        if target_type == "thenable":
            if key == "value" and self._get_devtools_thenable_status(target) == "fulfilled":
                return (self._get_devtools_thenable_value(target), True)
            if key == "reason" and self._get_devtools_thenable_status(target) == "rejected":
                return (self._get_devtools_thenable_reason(target), True)
        if target_type == "react_lazy" and key == "_payload":
            return (getattr(target, "_payload", None), True)
        if target_type == "typed_array":
            if isinstance(key, int) and 0 <= key < len(target):
                return (target[key], True)
        if target_type in {"iterator", "html_all_collection"}:
            items = self._get_devtools_iterator_items(target)
            if isinstance(key, int) and 0 <= key < len(items):
                return (items[key], True)

        return (None, False)

    def _get_nested_value(
        self,
        target: Any,
        path: list[Any],
    ) -> tuple[Any, bool]:
        current = target
        for key in path:
            current, found = self._get_devtools_named_value(current, key)
            if not found:
                return (None, False)
        return (self._clone_devtools_value(current), True)

    def _set_nested_value(self, target: Any, path: list[Any], value: Any) -> bool:
        if not path:
            if isinstance(value, dict):
                target.clear()
                target.update(self._clone_devtools_value(value))
                return True
            return False
        current: Any = target
        for key in path[:-1]:
            if isinstance(key, int):
                if not isinstance(current, list):
                    return False
                while len(current) <= key:
                    current.append({})
                if not isinstance(current[key], (dict, list)):
                    current[key] = {}
                current = current[key]
                continue
            if not isinstance(current, dict):
                return False
            next_value = current.get(key)
            if not isinstance(next_value, (dict, list)):
                next_value = {}
                current[key] = next_value
            current = next_value
        last_key = path[-1]
        if isinstance(last_key, int):
            if not isinstance(current, list):
                return False
            while len(current) <= last_key:
                current.append(None)
            current[last_key] = self._clone_devtools_value(value)
            return True
        if not isinstance(current, dict):
            return False
        current[last_key] = self._clone_devtools_value(value)
        return True

    def _delete_nested_value(self, target: dict[str, Any], path: list[Any]) -> bool:
        if not path:
            return False
        parent, key, found = self._resolve_nested_parent(target, path)
        if not found:
            return False
        if isinstance(key, int):
            if 0 <= key < len(parent):
                parent.pop(key)
                return True
            return False
        parent.pop(key, None)
        return True

    def _pop_nested_value(self, target: dict[str, Any], path: list[Any]) -> tuple[Any, bool]:
        if not path:
            return (None, False)
        parent, key, found = self._resolve_nested_parent(target, path)
        if not found:
            return (None, False)
        if isinstance(key, int):
            if 0 <= key < len(parent):
                return (parent.pop(key), True)
            return (None, False)
        return (parent.pop(key), True)

    def _resolve_nested_parent(
        self,
        target: dict[str, Any],
        path: list[Any],
    ) -> tuple[Any, Any, bool]:
        current: Any = target
        for key in path[:-1]:
            if isinstance(key, int):
                if not isinstance(current, list) or key >= len(current):
                    return (None, None, False)
                current = current[key]
                continue
            if not isinstance(current, dict) or key not in current:
                return (None, None, False)
            current = current[key]
        return (current, path[-1], True)

    @staticmethod
    def _priority_rank(priority: UpdatePriority) -> int:
        if priority == "render_phase":
            return 2
        if priority == "discrete":
            return 1
        return 0

    def update_container(
        self,
        element: "RenderableNode",
        container: ReconcilerContainer,
        parent_component: Optional[Any] = None,
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Update the container with a new element tree.

        Args:
            element: The new element to render.
            container: The container info.
            parent_component: Parent component reference.
            callback: Optional callback after update.
        """
        if container.tag == 0:
            self.update_container_sync(
                element,
                container,
                parent_component=parent_component,
                callback=callback,
            )
            return

        with container.lock:
            container.pending_element = element
            container.pending_callback = callback
            if container.work_scheduled:
                return
            container.work_scheduled = True

        def run() -> None:
            while True:
                with container.lock:
                    next_element = container.pending_element
                    next_callback = container.pending_callback
                    container.pending_element = None
                    container.pending_callback = None

                self._commit_container_update(
                    next_element,
                    container,
                    parent_component=parent_component,
                    callback=next_callback,
                )

                with container.lock:
                    if container.pending_element is None:
                        container.work_scheduled = False
                        return

        threading.Thread(target=run, daemon=True).start()

    def update_container_sync(
        self,
        element: "RenderableNode",
        container: ReconcilerContainer,
        parent_component: Optional[Any] = None,
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """Synchronous container update."""
        self._commit_container_update(element, container, parent_component, callback)

    def flush_sync_work(self, container: Optional[ReconcilerContainer] = None) -> None:
        """Flush any pending synchronous work."""
        if container is None:
            return

        while True:
            with container.lock:
                element = container.pending_element
                callback = container.pending_callback
                container.pending_element = None
                container.pending_callback = None
                container.work_scheduled = False

            if element is None:
                return

            self._commit_container_update(element, container, callback=callback)

    def submit_container(
        self,
        element: "RenderableNode",
        container: ReconcilerContainer,
        parent_component: Optional[Any] = None,
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """Submit work using the container's scheduling mode."""
        if container.tag == 0:
            self.update_container_sync(
                element,
                container,
                parent_component=parent_component,
                callback=callback,
            )
            self.flush_sync_work(container)
            return

        self.update_container(
            element,
            container,
            parent_component=parent_component,
            callback=callback,
        )

    def batched_updates(self, callback: Callable[[], Any]) -> Any:
        """Compatibility surface mirroring React reconciler batchedUpdates()."""
        return _batched_updates_runtime(callback)

    def discrete_updates(self, callback: Callable[[], Any]) -> Any:
        """Compatibility surface mirroring React reconciler discreteUpdates()."""
        return _discrete_updates_runtime(callback)

    def request_rerender(
        self,
        container: ReconcilerContainer,
        *,
        priority: UpdatePriority,
    ) -> None:
        host_config = self._host_config
        if host_config is None:
            return

        with container.lock:
            container.rerender_requested = True
            if self._priority_rank(priority) > self._priority_rank(
                container.pending_rerender_priority
            ):
                container.pending_rerender_priority = priority
            if container.rerender_running:
                return
            container.rerender_running = True

        try:
            while True:
                with container.lock:
                    current_component = host_config.get_current_component()
                    if not container.rerender_requested or current_component is None:
                        container.rerender_running = False
                        return
                    container.rerender_requested = False
                    container.current_render_priority = container.pending_rerender_priority
                    container.pending_rerender_priority = "default"

                host_config.perform_render(current_component)
                if container.current_render_priority != "render_phase":
                    host_config.wait_for_render_flush(1.0)
        finally:
            with container.lock:
                container.rerender_running = False
                container.current_render_priority = "default"

    def drain_pending_rerenders(
        self,
        container: ReconcilerContainer,
    ) -> None:
        priority = _consume_pending_rerender_priority()
        if priority is None:
            return

        self.request_rerender(
            container,
            priority=priority,
        )

    def dispatch_commit_render(
        self,
        container: ReconcilerContainer,
    ) -> None:
        self._request_host_render(container.current_render_priority, immediate=False)

    def _commit_container_update(
        self,
        element: "RenderableNode",
        container: ReconcilerContainer,
        parent_component: Optional[Any] = None,
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        dom_container = container.container
        self._visited_class_component_ids.clear()
        self._pending_class_component_commit_callbacks.clear()
        self._pending_component_did_catch.clear()
        self._commit_phase_recovery_requested = False
        self._next_devtools_tree_snapshot = {
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
        self._next_devtools_effective_props = {}
        self._next_devtools_host_instance_ids = {id(self.root_node): "root"}
        root_inspected_element = {
            "id": "root",
            "canEditHooks": False,
            "canEditFunctionProps": False,
            "canEditHooksAndDeletePaths": False,
            "canEditHooksAndRenamePaths": False,
            "canEditFunctionPropsDeletePaths": False,
            "canEditFunctionPropsRenamePaths": False,
            "canToggleError": False,
            "isErrored": False,
            "canToggleSuspense": False,
            "isSuspended": None,
            "hasLegacyContext": False,
            "context": None,
            "hooks": None,
            "props": None,
            "state": None,
            "key": None,
            "errors": [],
            "warnings": [],
            "suspendedBy": [],
            "suspendedByRange": None,
            "unknownSuspenders": 0,
            "owners": None,
            "env": None,
            "source": None,
            "stack": None,
            "type": "root",
            "rootType": "pyinkcli",
            "rendererPackageName": packageInfo["name"],
            "rendererVersion": packageInfo["version"],
            "plugins": {"stylex": None},
            "nativeTag": None,
        }
        self._next_devtools_inspected_elements = {"root": root_inspected_element}
        self._next_devtools_inspected_element_fingerprints = {
            "root": self._build_devtools_fingerprint(root_inspected_element)
        }
        commit_phase_recovery_needed = False

        try:
            next_index = 0
            if element is not None:
                next_index = self._reconcile_children(
                    dom_container,
                    [element],
                    (),
                    0,
                    "root",
                )

            self._remove_extra_children(dom_container, next_index)
        finally:
            _finish_hook_state()
        self._finalize_devtools_tree_snapshot()
        self._dispose_stale_class_component_instances()
        commit_phase_recovery_needed = self._flush_class_component_commit_callbacks()
        self._after_commit(container)
        self._flush_component_did_catch_callbacks(
            include_deferred=not commit_phase_recovery_needed,
        )

        if commit_phase_recovery_needed:
            self.request_rerender(container, priority="default")

        if callback:
            callback()

    def _after_commit(self, container: ReconcilerContainer) -> None:
        dom_container = container.container
        if callable(dom_container.on_compute_layout):
            dom_container.on_compute_layout()
        elif dom_container.yoga_node:
            self._calculate_layout(dom_container)

        emitLayoutListeners(dom_container)

        if dom_container.is_static_dirty:
            dom_container.is_static_dirty = False
            self._request_host_render(container.current_render_priority, immediate=True)
            return

        self._request_host_render(container.current_render_priority, immediate=False)

    def _request_host_render(
        self,
        priority: UpdatePriority,
        *,
        immediate: bool,
    ) -> None:
        if self._host_config is not None:
            self._host_config.request_render(priority, immediate)
            return

        if immediate:
            if self._on_immediate_commit is not None:
                self._on_immediate_commit()
            return

        if self._on_commit is not None:
            self._on_commit()

    def _reconcile_children(
        self,
        parent: DOMElement,
        children: List["RenderableNode"],
        path: tuple[Any, ...],
        dom_index: int,
        devtools_parent_id: str,
    ) -> int:
        """
        Reconcile children into a parent node.

        Args:
            parent: The parent DOM element.
            children: List of child vnodes.
        """
        for index, child in enumerate(children):
            child_path = path + (self._get_child_path_token(child, index),)
            dom_index = self._reconcile_child(
                child,
                parent,
                child_path,
                dom_index,
                devtools_parent_id,
            )

        return dom_index

    def _reconcile_child(
        self,
        vnode: "RenderableNode",
        parent: DOMElement,
        path: tuple[Any, ...],
        dom_index: int,
        devtools_parent_id: str,
    ) -> int:
        if vnode is None:
            return dom_index

        context_manager_factories = getattr(vnode, "context_manager_factories", None)
        if context_manager_factories is not None:
            with ExitStack() as stack:
                for factory in context_manager_factories:
                    stack.enter_context(factory())
                return self._reconcile_child(
                    vnode.node,
                    parent,
                    path,
                    dom_index,
                    devtools_parent_id,
                )

        if isinstance(vnode, str):
            host_context = self._host_context_stack[-1]
            if not host_context.get("is_inside_text", False):
                raise ValueError(
                    f'Text string "{vnode[:20]}..." must be rendered inside <Text> component'
                )

            self._reconcile_text_node(parent, vnode, dom_index)
            return dom_index + 1

        node_type = vnode.type
        props = dict(vnode.props)
        children = list(vnode.children)

        if node_type == "__ink-suspense__":
            suspense_id = self._append_devtools_node(
                node_id=self._build_devtools_node_id("Suspense", path, vnode.key),
                parent_id=devtools_parent_id,
                display_name="Suspense",
                element_type="suspense",
                key=vnode.key,
                is_error_boundary=False,
            )
            self._record_devtools_inspected_element(
                node_id=suspense_id,
                element_type="suspense",
                key=vnode.key,
                props=props,
                can_toggle_error=bool(self._error_boundary_stack),
                can_toggle_suspense=True,
                is_suspended=False,
                nearest_error_boundary_id=(
                    self._error_boundary_stack[-1][0] if self._error_boundary_stack else None
                ),
                nearest_suspense_boundary_id=suspense_id,
                owners=self._serialize_devtools_owner_stack(),
                source=self._get_current_owner_source(),
                stack=self._build_devtools_stack(self._owner_component_stack),
            )
            if suspense_id in self._devtools_forced_suspense_boundaries:
                self._record_devtools_inspected_element(
                    node_id=suspense_id,
                    element_type="suspense",
                    key=vnode.key,
                    props=props,
                    can_toggle_error=bool(self._error_boundary_stack),
                    can_toggle_suspense=True,
                    is_suspended=True,
                    nearest_error_boundary_id=(
                        self._error_boundary_stack[-1][0] if self._error_boundary_stack else None
                    ),
                    nearest_suspense_boundary_id=suspense_id,
                    owners=self._serialize_devtools_owner_stack(),
                    source=self._get_current_owner_source(),
                    stack=self._build_devtools_stack(self._owner_component_stack),
                )
                fallback = props.get("fallback")
                if fallback is None:
                    return dom_index
                self._suspense_boundary_stack.append(suspense_id)
                try:
                    return self._reconcile_child(
                        fallback,
                        parent,
                        path + ("fallback",),
                        dom_index,
                        suspense_id,
                    )
                finally:
                    self._suspense_boundary_stack.pop()
            fallback = props.get("fallback")
            self._suspense_boundary_stack.append(suspense_id)
            try:
                return self._reconcile_children(
                    parent,
                    children,
                    path,
                    dom_index,
                    suspense_id,
                )
            except SuspendSignal as signal:
                self._record_devtools_inspected_element(
                    node_id=suspense_id,
                    element_type="suspense",
                    key=vnode.key,
                    props=props,
                    can_toggle_error=bool(self._error_boundary_stack),
                    can_toggle_suspense=True,
                    is_suspended=True,
                    nearest_error_boundary_id=(
                        self._error_boundary_stack[-1][0] if self._error_boundary_stack else None
                    ),
                    nearest_suspense_boundary_id=suspense_id,
                    owners=self._serialize_devtools_owner_stack(),
                    source=self._get_current_owner_source(),
                    stack=self._build_devtools_stack(self._owner_component_stack),
                    suspended_by=[
                        {
                            "name": "SuspendSignal",
                            "awaited": {
                                "value": {
                                    "resource": {
                                        "key": repr(signal.key),
                                    },
                                    "message": str(signal),
                                }
                            },
                            "env": None,
                            "owner": None,
                            "stack": None,
                        }
                    ],
                )
                if fallback is None:
                    return dom_index
                return self._reconcile_child(
                    fallback,
                    parent,
                    path + ("fallback",),
                    dom_index,
                    suspense_id,
                )
            finally:
                self._suspense_boundary_stack.pop()

        if is_component(node_type):
            component_id = self._get_component_instance_id(node_type, vnode, path)
            props = self._get_effective_devtools_props(component_id, props)
            display_name = self._get_component_display_name(node_type)
            component_source = self._get_source_for_target(node_type, display_name)
            owner_entry = {
                "id": component_id,
                "displayName": display_name,
                "elementType": "class" if _is_component_class(node_type) else "function",
                "key": vnode.key,
                "source": component_source,
            }
            if _is_component_class(node_type):
                self._append_devtools_node(
                    node_id=component_id,
                    parent_id=devtools_parent_id,
                    display_name=display_name,
                    element_type="class",
                    key=vnode.key,
                    is_error_boundary=self._is_component_type_error_boundary(node_type),
                )
                return self._reconcile_class_component(
                    component_type=node_type,
                    component_id=component_id,
                    props=props,
                    children=children,
                    parent=parent,
                    path=path,
                    dom_index=dom_index,
                    devtools_parent_id=component_id,
                    vnode_key=vnode.key,
                    owner_entry=owner_entry,
                )
            self._append_devtools_node(
                node_id=component_id,
                parent_id=devtools_parent_id,
                display_name=display_name,
                element_type="function",
                key=vnode.key,
                is_error_boundary=False,
            )
            _begin_component_render(component_id)
            try:
                rendered = renderComponent(node_type, *children, **props)
            finally:
                _end_component_render()
            self._record_devtools_inspected_element(
                node_id=component_id,
                element_type="function",
                key=vnode.key,
                props=props,
                hooks=_get_hook_state_snapshot(component_id),
                can_edit_hooks=True,
                can_edit_function_props=True,
                can_toggle_error=bool(self._error_boundary_stack),
                can_toggle_suspense=bool(self._suspense_boundary_stack),
                nearest_error_boundary_id=(
                    self._error_boundary_stack[-1][0] if self._error_boundary_stack else None
                ),
                nearest_suspense_boundary_id=(
                    self._suspense_boundary_stack[-1] if self._suspense_boundary_stack else None
                ),
                owners=self._serialize_devtools_owner_stack(),
                source=component_source,
                stack=self._build_devtools_stack(
                    self._owner_component_stack,
                    current_entry=owner_entry,
                ),
            )

            self._owner_component_stack.append(owner_entry)
            try:
                return self._reconcile_child(
                    rendered,
                    parent,
                    path,
                    dom_index,
                    component_id,
                )
            finally:
                self._owner_component_stack.pop()

        if node_type is _Fragment or node_type == "Fragment":
            fragment_id = self._append_devtools_node(
                node_id=self._build_devtools_node_id("Fragment", path, vnode.key),
                parent_id=devtools_parent_id,
                display_name="Fragment",
                element_type="fragment",
                key=vnode.key,
                is_error_boundary=False,
            )
            self._record_devtools_inspected_element(
                node_id=fragment_id,
                element_type="fragment",
                key=vnode.key,
                can_toggle_error=bool(self._error_boundary_stack),
                can_toggle_suspense=bool(self._suspense_boundary_stack),
                nearest_error_boundary_id=(
                    self._error_boundary_stack[-1][0] if self._error_boundary_stack else None
                ),
                nearest_suspense_boundary_id=(
                    self._suspense_boundary_stack[-1] if self._suspense_boundary_stack else None
                ),
                owners=self._serialize_devtools_owner_stack(),
                source=self._get_current_owner_source(),
                stack=self._build_devtools_stack(self._owner_component_stack),
            )
            return self._reconcile_children(parent, children, path, dom_index, fragment_id)

        element_name = self._get_element_name(node_type)
        if element_name is None:
            return dom_index

        host_context = self._host_context_stack[-1]
        is_inside_text = host_context.get("is_inside_text", False)

        if is_inside_text and element_name == "ink-box":
            raise ValueError("<Box> can't be nested inside <Text> component")

        actual_type = element_name
        if element_name == "ink-text" and is_inside_text:
            actual_type = "ink-virtual-text"

        host_node_id = self._append_devtools_node(
            node_id=self._build_devtools_node_id(actual_type, path, vnode.key),
            parent_id=devtools_parent_id,
            display_name=actual_type,
            element_type="host",
            key=vnode.key,
            is_error_boundary=False,
        )
        self._record_devtools_inspected_element(
            node_id=host_node_id,
            element_type="host",
            key=vnode.key,
            props=props,
            can_toggle_error=bool(self._error_boundary_stack),
            can_toggle_suspense=bool(self._suspense_boundary_stack),
            nearest_error_boundary_id=(
                self._error_boundary_stack[-1][0] if self._error_boundary_stack else None
            ),
            nearest_suspense_boundary_id=(
                self._suspense_boundary_stack[-1] if self._suspense_boundary_stack else None
            ),
            owners=self._serialize_devtools_owner_stack(),
            source=self._get_current_owner_source(),
            stack=self._build_devtools_stack(self._owner_component_stack),
        )

        dom_node = self._reconcile_element_node(
            parent,
            actual_type,
            props,
            children,
            path,
            dom_index,
            vnode.key,
        )
        if self._next_devtools_host_instance_ids is not None:
            self._next_devtools_host_instance_ids[id(dom_node)] = host_node_id

        new_host_context = {
            "is_inside_text": actual_type in ("ink-text", "ink-virtual-text")
        }
        self._host_context_stack.append(new_host_context)
        try:
            next_child_index = self._reconcile_children(
                dom_node,
                children,
                path,
                0,
                host_node_id,
            )
            self._remove_extra_children(dom_node, next_child_index)
        finally:
            self._host_context_stack.pop()

        return dom_index + 1

    def _reconcile_class_component(
        self,
        *,
        component_type: type[_Component],
        component_id: str,
        props: dict[str, Any],
        children: list["RenderableNode"],
        parent: DOMElement,
        path: tuple[Any, ...],
        dom_index: int,
        devtools_parent_id: str,
        vnode_key: Optional[str],
        owner_entry: dict[str, Any],
    ) -> int:
        instance, is_new_instance, previous_props, previous_state = self._get_or_create_class_component_instance(
            component_type,
            component_id,
            tuple(children),
            props,
        )
        instance._nearest_error_boundary = (
            self._error_boundary_stack[-1][2] if self._error_boundary_stack else None
        )
        should_update = True
        if (
            not is_new_instance
            and callable(getattr(instance, "shouldComponentUpdate", None))
        ):
            should_update = bool(
                instance.shouldComponentUpdate(
                    dict(instance.props),
                    dict(instance.state),
                )
            )

        is_error_boundary = self._is_error_boundary(component_type, instance)
        if component_id in self._devtools_forced_error_boundaries and is_error_boundary:
            self._apply_error_boundary_state(
                component_type,
                instance,
                _DevtoolsForcedError("DevTools forced error"),
            )

        if should_update or instance._last_rendered_node is None:
            rendered = instance.render()
            instance._last_rendered_node = rendered
        else:
            rendered = instance._last_rendered_node

        self._record_devtools_inspected_element(
            node_id=component_id,
            element_type="class",
            key=vnode_key,
            props=dict(instance.props),
            state=dict(instance.state),
            context=None,
            can_edit_hooks=False,
            can_edit_function_props=False,
            can_toggle_error=is_error_boundary or bool(self._error_boundary_stack),
            is_errored=component_id in self._devtools_forced_error_boundaries
            or bool(instance.state.get("error")),
            can_toggle_suspense=bool(self._suspense_boundary_stack),
            nearest_error_boundary_id=(
                component_id
                if is_error_boundary
                else (self._error_boundary_stack[-1][0] if self._error_boundary_stack else None)
            ),
            nearest_suspense_boundary_id=(
                self._suspense_boundary_stack[-1] if self._suspense_boundary_stack else None
            ),
            owners=self._serialize_devtools_owner_stack(),
            source=owner_entry.get("source"),
            stack=self._build_devtools_stack(
                self._owner_component_stack,
                current_entry=owner_entry,
            ),
        )

        self._schedule_class_component_commit_callback(
            instance,
            is_new_instance=is_new_instance,
            should_update=should_update,
            previous_props=previous_props,
            previous_state=previous_state,
        )

        self._owner_component_stack.append(owner_entry)
        if not is_error_boundary:
            try:
                return self._reconcile_child(
                    rendered,
                    parent,
                    path,
                    dom_index,
                    devtools_parent_id,
                )
            finally:
                self._owner_component_stack.pop()

        self._error_boundary_stack.append((component_id, component_type, instance))
        try:
            return self._reconcile_child(
                rendered,
                parent,
                path,
                dom_index,
                devtools_parent_id,
            )
        except Exception as error:
            fallback = self._render_error_boundary_fallback(
                component_type,
                instance,
                error,
            )
            self._record_devtools_inspected_element(
                node_id=component_id,
                element_type="class",
                key=vnode_key,
                props=dict(instance.props),
                state=dict(instance.state),
                context=None,
                can_edit_hooks=False,
                can_edit_function_props=False,
                can_toggle_error=True,
                is_errored=bool(instance.state.get("error")),
                can_toggle_suspense=bool(self._suspense_boundary_stack),
                nearest_error_boundary_id=component_id,
                nearest_suspense_boundary_id=(
                    self._suspense_boundary_stack[-1] if self._suspense_boundary_stack else None
                ),
                owners=self._serialize_devtools_owner_stack(),
                source=owner_entry.get("source"),
                stack=self._build_devtools_stack(
                    self._owner_component_stack,
                    current_entry=owner_entry,
                ),
            )
            return self._reconcile_child(
                fallback,
                parent,
                path,
                dom_index,
                devtools_parent_id,
            )
        finally:
            self._error_boundary_stack.pop()
            self._owner_component_stack.pop()

    def _reconcile_text_node(
        self,
        parent: DOMElement,
        text: str,
        dom_index: int,
    ) -> None:
        existing = self._get_existing_child(parent, dom_index)

        if isinstance(existing, TextNode):
            setTextNodeValue(existing, text)
            return

        new_node = createTextNode(text)
        self._insert_or_replace_child(parent, new_node, dom_index)

    def _reconcile_element_node(
        self,
        parent: DOMElement,
        actual_type: str,
        props: dict[str, Any],
        children: list["RenderableNode"],
        path: tuple[Any, ...],
        dom_index: int,
        vnode_key: Optional[str],
    ) -> DOMElement:
        current_existing = self._get_existing_child(parent, dom_index)
        existing = self._find_matching_child(parent, dom_index, actual_type, vnode_key)

        if isinstance(existing, DOMElement) and existing.node_name == actual_type:
            dom_node = existing
            if current_existing is not None and current_existing is not dom_node:
                insertBeforeNode(parent, dom_node, current_existing)
        else:
            dom_node = createNode(actual_type)
            self._insert_or_replace_child(parent, dom_node, dom_index)

        self._apply_props(dom_node, props, vnode_key)
        return dom_node

    def _apply_props(
        self,
        dom_node: DOMElement,
        props: dict[str, Any],
        vnode_key: Optional[str],
    ) -> None:
        style = props.pop("style", {})
        setStyle(dom_node, style)
        if dom_node.yoga_node:
            apply_styles(dom_node.yoga_node, style)

        dom_node.internal_key = vnode_key
        dom_node.internal_transform = props.pop("internal_transform", None)

        internal_static = bool(props.pop("internal_static", False))
        dom_node.internal_static = internal_static
        if internal_static:
            self.root_node.is_static_dirty = True
            self.root_node.static_node = dom_node
        elif self.root_node.static_node is dom_node:
            self.root_node.static_node = None

        internal_accessibility = props.pop("internal_accessibility", None)
        if internal_accessibility is None:
            dom_node.internal_accessibility = AccessibilityInfo()
        elif isinstance(internal_accessibility, AccessibilityInfo):
            dom_node.internal_accessibility = internal_accessibility
        else:
            dom_node.internal_accessibility = AccessibilityInfo(
                role=internal_accessibility.get("role"),
                state=internal_accessibility.get("state"),
            )

        new_attributes = {
            key: value
            for key, value in props.items()
            if key not in ("children", "ref")
        }

        for key in list(dom_node.attributes.keys()):
            if key not in new_attributes:
                del dom_node.attributes[key]

        for key, value in new_attributes.items():
            setAttribute(dom_node, key, value)

    def _get_existing_child(
        self,
        parent: DOMElement,
        dom_index: int,
    ) -> Optional[DOMNode]:
        if 0 <= dom_index < len(parent.child_nodes):
            return parent.child_nodes[dom_index]

        return None

    def _find_matching_child(
        self,
        parent: DOMElement,
        dom_index: int,
        actual_type: str,
        vnode_key: Optional[str],
    ) -> Optional[DOMNode]:
        existing = self._get_existing_child(parent, dom_index)
        if (
            isinstance(existing, DOMElement)
            and existing.node_name == actual_type
            and existing.internal_key == vnode_key
        ):
            return existing

        if vnode_key is None:
            return existing

        for child in parent.child_nodes[dom_index + 1:]:
            if (
                isinstance(child, DOMElement)
                and child.node_name == actual_type
                and child.internal_key == vnode_key
            ):
                return child

        return existing

    def _insert_or_replace_child(
        self,
        parent: DOMElement,
        child: DOMNode,
        dom_index: int,
    ) -> None:
        existing = self._get_existing_child(parent, dom_index)
        if existing is child:
            return

        if existing is None:
            appendChildNode(parent, child)
            return

        if child.parent_node is parent:
            insertBeforeNode(parent, child, existing)
            return

        insertBeforeNode(parent, child, existing)
        removeChildNode(parent, existing)
        self._dispose_node(existing)

    def _remove_extra_children(self, parent: DOMElement, start_index: int) -> None:
        while len(parent.child_nodes) > start_index:
            child = parent.child_nodes[start_index]
            removeChildNode(parent, child)
            self._dispose_node(child)

    def _dispose_node(self, node: DOMNode) -> None:
        if isinstance(node, DOMElement):
            while node.child_nodes:
                child = node.child_nodes[0]
                removeChildNode(node, child)
                self._dispose_node(child)

            if self.root_node.static_node is node:
                self.root_node.static_node = None

            if node.yoga_node is not None and hasattr(node.yoga_node, "free"):
                node.yoga_node.free()

    def _get_component_instance_id(
        self,
        component_type: Any,
        vnode: "RenderableNode",
        path: tuple[Any, ...],
    ) -> str:
        assert isElement(vnode)
        component_name = getattr(component_type, "_component_name", None)
        if component_name is None:
            component_name = getattr(component_type, "displayName", None)
        if component_name is None:
            component_name = getattr(component_type, "__name__", repr(component_type))

        key = vnode.key if vnode.key is not None else ""
        return f"{component_name}:{'.'.join(str(part) for part in path)}:{key}"

    def _get_component_display_name(self, component_type: Any) -> str:
        display_name = getattr(component_type, "_component_name", None)
        if display_name is None:
            display_name = getattr(component_type, "displayName", None)
        if display_name is None:
            display_name = getattr(component_type, "__name__", repr(component_type))
        return str(display_name)

    def _is_component_type_error_boundary(self, component_type: type[_Component]) -> bool:
        return callable(getattr(component_type, "getDerivedStateFromError", None))

    def _build_devtools_node_id(
        self,
        display_name: str,
        path: tuple[Any, ...],
        key: Optional[str],
    ) -> str:
        path_value = ".".join(str(part) for part in path)
        key_value = key or ""
        return f"{display_name}:{path_value}:{key_value}"

    def _append_devtools_node(
        self,
        *,
        node_id: str,
        parent_id: str,
        display_name: str,
        element_type: str,
        key: Optional[str],
        is_error_boundary: bool,
    ) -> str:
        snapshot = self._next_devtools_tree_snapshot
        if snapshot is None:
            return node_id
        nodes = snapshot["nodes"]
        for existing in nodes:
            if existing["id"] == node_id:
                return node_id
        nodes.append(
            {
                "id": node_id,
                "parentID": parent_id,
                "displayName": display_name,
                "elementType": element_type,
                "key": key,
                "isErrorBoundary": is_error_boundary,
            }
        )
        return node_id

    def _record_devtools_inspected_element(
        self,
        *,
        node_id: str,
        element_type: str,
        key: Optional[str],
        props: Optional[dict[str, Any]] = None,
        state: Optional[dict[str, Any]] = None,
        hooks: Optional[list[dict[str, Any]]] = None,
        context: Optional[dict[str, Any]] = None,
        can_edit_hooks: bool = False,
        can_edit_function_props: bool = False,
        can_toggle_error: bool = False,
        is_errored: bool = False,
        can_toggle_suspense: bool = False,
        is_suspended: Optional[bool] = None,
        nearest_error_boundary_id: Optional[str] = None,
        nearest_suspense_boundary_id: Optional[str] = None,
        owners: Optional[list[dict[str, Any]]] = None,
        source: Optional[list[Any]] = None,
        stack: Optional[list[list[Any]]] = None,
        suspended_by: Optional[list[Any]] = None,
    ) -> None:
        target = self._next_devtools_inspected_elements
        if target is None:
            return
        if nearest_error_boundary_id is not None:
            self._devtools_nearest_error_boundary_by_node[node_id] = nearest_error_boundary_id
        if nearest_suspense_boundary_id is not None:
            self._devtools_nearest_suspense_boundary_by_node[node_id] = nearest_suspense_boundary_id
        target[node_id] = {
            "id": node_id,
            "canEditHooks": can_edit_hooks,
            "canEditFunctionProps": can_edit_function_props,
            "canEditHooksAndDeletePaths": can_edit_hooks,
            "canEditHooksAndRenamePaths": can_edit_hooks,
            "canEditFunctionPropsDeletePaths": can_edit_function_props,
            "canEditFunctionPropsRenamePaths": can_edit_function_props,
            "canToggleError": can_toggle_error,
            "isErrored": is_errored,
            "canToggleSuspense": can_toggle_suspense,
            "isSuspended": is_suspended,
            "hasLegacyContext": False,
            "context": self._clone_devtools_value(context) if context is not None else None,
            "hooks": self._clone_devtools_value(hooks) if hooks is not None else None,
            "props": self._clone_devtools_value(props) if props is not None else None,
            "state": self._clone_devtools_value(state) if state is not None else None,
            "key": key,
            "errors": [],
            "warnings": [],
            "suspendedBy": self._clone_devtools_value(suspended_by)
            if suspended_by is not None
            else [],
            "suspendedByRange": None,
            "unknownSuspenders": 0,
            "owners": self._clone_devtools_value(owners) if owners is not None else None,
            "env": None,
            "source": self._clone_devtools_value(source) if source is not None else None,
            "stack": self._clone_devtools_value(stack) if stack is not None else None,
            "type": element_type,
            "rootType": "pyinkcli",
            "rendererPackageName": packageInfo["name"],
            "rendererVersion": packageInfo["version"],
            "plugins": {"stylex": None},
            "nativeTag": None,
        }
        if suspended_by:
            root_element = target.get("root")
            if isinstance(root_element, dict):
                root_suspended_by = root_element.setdefault("suspendedBy", [])
                if isinstance(root_suspended_by, list):
                    root_suspended_by.extend(self._clone_devtools_value(suspended_by))
        fingerprints = self._next_devtools_inspected_element_fingerprints
        if fingerprints is not None:
            fingerprints[node_id] = self._build_devtools_fingerprint(target[node_id])
            root_element = target.get("root")
            if isinstance(root_element, dict):
                fingerprints["root"] = self._build_devtools_fingerprint(root_element)

    def _get_source_for_target(
        self,
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

    def _make_call_site(
        self,
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

    def _serialize_devtools_owner_stack(self) -> Optional[list[dict[str, Any]]]:
        if not self._owner_component_stack:
            return None
        owners: list[dict[str, Any]] = []
        ancestry: list[dict[str, Any]] = []
        for entry in reversed(self._owner_component_stack):
            ancestry.insert(0, entry)
            owners.append(
                {
                    "displayName": entry["displayName"],
                    "id": entry["id"],
                    "key": entry["key"],
                    "env": None,
                    "stack": self._build_devtools_stack(ancestry),
                    "type": entry["elementType"],
                }
            )
        return owners

    def _build_devtools_stack(
        self,
        entries: list[dict[str, Any]],
        *,
        current_entry: Optional[dict[str, Any]] = None,
    ) -> Optional[list[list[Any]]]:
        frames: list[list[Any]] = []
        if current_entry is not None:
            current_frame = self._make_call_site(
                current_entry["displayName"],
                current_entry.get("source"),
            )
            if current_frame is not None:
                frames.append(current_frame)
        for entry in reversed(entries):
            frame = self._make_call_site(entry["displayName"], entry.get("source"))
            if frame is not None:
                frames.append(frame)
        return frames or None

    def _get_current_owner_source(self) -> Optional[list[Any]]:
        if not self._owner_component_stack:
            return None
        return self._clone_devtools_value(self._owner_component_stack[-1].get("source"))

    def _finalize_devtools_tree_snapshot(self) -> None:
        if self._next_devtools_tree_snapshot is None:
            return

        if self._devtools_most_recently_inspected_id is not None:
            previous_fingerprint = self._devtools_inspected_element_fingerprints.get(
                self._devtools_most_recently_inspected_id
            )
            next_fingerprint = None
            if self._next_devtools_inspected_element_fingerprints is not None:
                next_fingerprint = self._next_devtools_inspected_element_fingerprints.get(
                    self._devtools_most_recently_inspected_id
                )
            self._devtools_has_element_updated_since_last_inspected = (
                previous_fingerprint != next_fingerprint
            )

        self._devtools_tree_snapshot = self._next_devtools_tree_snapshot
        self._next_devtools_tree_snapshot = None
        if self._next_devtools_effective_props is not None:
            self._devtools_effective_props = self._next_devtools_effective_props
            self._next_devtools_effective_props = None
        if self._next_devtools_inspected_elements is not None:
            self._devtools_inspected_elements = self._next_devtools_inspected_elements
            self._next_devtools_inspected_elements = None
        if self._next_devtools_inspected_element_fingerprints is not None:
            self._devtools_inspected_element_fingerprints = (
                self._next_devtools_inspected_element_fingerprints
            )
            self._next_devtools_inspected_element_fingerprints = None
        if self._next_devtools_host_instance_ids is not None:
            self._devtools_host_instance_ids = self._next_devtools_host_instance_ids
            self._next_devtools_host_instance_ids = None

    def _get_effective_devtools_props(
        self,
        node_id: str,
        props: dict[str, Any],
    ) -> dict[str, Any]:
        base_props = self._clone_devtools_value(props)
        override_props = self._devtools_prop_overrides.get(node_id)
        effective_props = (
            self._clone_devtools_value(override_props)
            if override_props is not None
            else base_props
        )
        target = self._next_devtools_effective_props
        if target is not None:
            target[node_id] = self._clone_devtools_value(effective_props)
        else:
            self._devtools_effective_props[node_id] = self._clone_devtools_value(effective_props)
        return effective_props

    def _get_or_create_class_component_instance(
        self,
        component_type: type[_Component],
        component_id: str,
        children: tuple["RenderableNode", ...],
        props: dict[str, Any],
    ) -> tuple[_Component, bool, dict[str, Any], dict[str, Any]]:
        self._visited_class_component_ids.add(component_id)
        instance = self._class_component_instances.get(component_id)
        merged_props = _merge_component_props(children, props)

        if instance is None or not isinstance(instance, component_type):
            instance = _create_component_instance(component_type, children, props)
            self._class_component_instances[component_id] = instance
            return (instance, True, {}, {})

        previous_props = dict(instance.props)
        previous_state = (
            dict(instance._pending_previous_state)
            if instance._pending_previous_state is not None
            else dict(instance.state)
        )
        instance._pending_previous_state = None
        instance.props = merged_props
        instance._is_unmounted = False
        return (instance, False, previous_props, previous_state)

    def _schedule_class_component_commit_callback(
        self,
        instance: _Component,
        *,
        is_new_instance: bool,
        should_update: bool,
        previous_props: dict[str, Any],
        previous_state: dict[str, Any],
    ) -> None:
        if is_new_instance:
            if callable(getattr(instance, "componentDidMount", None)):
                self._pending_class_component_commit_callbacks.append(
                    (instance, lambda: self._invoke_component_did_mount(instance))
                )
            else:
                instance._is_mounted = True
            return

        if (
            not is_new_instance
            and should_update
            and callable(getattr(instance, "componentDidUpdate", None))
        ):
            self._pending_class_component_commit_callbacks.append(
                (
                    instance,
                    lambda: self._invoke_component_did_update(
                        instance,
                        previous_props,
                        previous_state,
                    ),
                )
            )

    def _invoke_component_did_mount(self, instance: _Component) -> None:
        instance._is_mounted = True
        instance.componentDidMount()

    def _invoke_component_did_update(
        self,
        instance: _Component,
        previous_props: dict[str, Any],
        previous_state: dict[str, Any],
    ) -> None:
        instance._is_mounted = True
        instance.componentDidUpdate(previous_props, previous_state)

    def _flush_class_component_commit_callbacks(self) -> bool:
        callbacks = self._pending_class_component_commit_callbacks[:]
        self._pending_class_component_commit_callbacks.clear()
        if not callbacks:
            return self._commit_phase_recovery_requested

        unhandled_error: Optional[Exception] = None

        def run_callbacks() -> None:
            nonlocal unhandled_error
            for instance, callback in callbacks:
                try:
                    callback()
                except Exception as error:
                    if self._capture_commit_phase_error(instance, error):
                        continue
                    if unhandled_error is None:
                        unhandled_error = error

        _batched_updates_runtime(run_callbacks)
        if unhandled_error is not None:
            raise unhandled_error
        return self._commit_phase_recovery_requested

    def cleanup_class_component_instances(self) -> None:
        component_ids = list(self._class_component_instances.keys())
        for component_id in component_ids:
            instance = self._class_component_instances.pop(component_id, None)
            if instance is None:
                continue
            self._unmount_class_component_instance(instance)

    def _dispose_stale_class_component_instances(self) -> None:
        stale_component_ids = [
            component_id
            for component_id in self._class_component_instances
            if component_id not in self._visited_class_component_ids
        ]
        for component_id in stale_component_ids:
            instance = self._class_component_instances.pop(component_id, None)
            if instance is None:
                continue
            self._unmount_class_component_instance(instance)

    def _unmount_class_component_instance(self, instance: _Component) -> None:
        instance._is_unmounted = True
        if not callable(getattr(instance, "componentWillUnmount", None)):
            return
        try:
            instance.componentWillUnmount()
        except Exception as error:
            if not self._capture_commit_phase_error(instance, error):
                raise

    def _capture_commit_phase_error(
        self,
        instance: _Component,
        error: Exception,
    ) -> bool:
        boundary = getattr(instance, "_nearest_error_boundary", None)
        if boundary is None or getattr(boundary, "_is_unmounted", False):
            return False

        derived_state = getattr(type(boundary), "getDerivedStateFromError", None)
        if callable(derived_state):
            next_state = derived_state(error)
            if isinstance(next_state, dict):
                boundary.state.update(next_state)
                boundary._state_version += 1

        self._deferred_component_did_catch.append((boundary, error))
        self._commit_phase_recovery_requested = True
        return True

    def _is_error_boundary(
        self,
        component_type: type[_Component],
        instance: _Component,
    ) -> bool:
        return callable(getattr(component_type, "getDerivedStateFromError", None)) or callable(
            getattr(instance, "componentDidCatch", None)
        )

    def _render_error_boundary_fallback(
        self,
        component_type: type[_Component],
        instance: _Component,
        error: Exception,
    ) -> "RenderableNode":
        self._apply_error_boundary_state(component_type, instance, error)

        if callable(getattr(instance, "componentDidCatch", None)):
            self._pending_component_did_catch.append((instance, error))

        return renderComponent(instance)

    def _apply_error_boundary_state(
        self,
        component_type: type[_Component],
        instance: _Component,
        error: Exception,
    ) -> None:
        derived_state = getattr(component_type, "getDerivedStateFromError", None)
        if not callable(derived_state):
            return
        if instance._pending_previous_state is None:
            instance._pending_previous_state = dict(instance.state)
        next_state = derived_state(error)
        if isinstance(next_state, dict):
            instance.state.update(next_state)
            instance._state_version += 1

    def _flush_component_did_catch_callbacks(self, *, include_deferred: bool) -> None:
        pending_callbacks = self._pending_component_did_catch[:]
        self._pending_component_did_catch.clear()
        if include_deferred:
            pending_callbacks.extend(self._deferred_component_did_catch)
            self._deferred_component_did_catch.clear()
        for instance, error in pending_callbacks:
            try:
                instance.componentDidCatch(error)
            except Exception:
                pass

    def _get_child_path_token(
        self,
        child: "RenderableNode",
        index: int,
    ) -> Any:
        if isElement(child) and child.key is not None:
            return f"key:{child.key}"

        return index

    def _get_element_name(self, node_type: Any) -> Optional[str]:
        """
        Get the DOM element name for a component type.

        Args:
            node_type: The component type.

        Returns:
            The element name or None.
        """
        if isinstance(node_type, str):
            # Map common names
            type_map = {
                "Box": "ink-box",
                "Text": "ink-text",
                "ink-box": "ink-box",
                "ink-text": "ink-text",
            }
            return type_map.get(node_type, node_type)

        return None

    def _calculate_layout(self, root: DOMElement) -> None:
        """
        Calculate the Yoga layout for the tree.

        Args:
            root: The root element.
        """
        from pyinkcli import _yoga as yoga

        if root.yoga_node:
            root.yoga_node.calculate_layout(
                yoga.UNDEFINED,
                yoga.UNDEFINED,
                yoga.DIRECTION_LTR,
            )


# Singleton reconciler instance
_reconciler_instance: Optional[_Reconciler] = None
currentUpdatePriority = 0


def diff(before: Dict[str, Any], after: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if before == after:
        return None
    if not before:
        return after
    changed: Dict[str, Any] = {}
    changed_any = False
    for key in before:
        if key not in after:
            changed[key] = None
            changed_any = True
    for key, value in after.items():
        if before.get(key) != value:
            changed[key] = value
            changed_any = True
    return changed if changed_any else None


def cleanupYogaNode(node: Optional[Any]) -> None:
    if node is None:
        return
    unset = getattr(node, "unset_measure_func", None) or getattr(node, "unsetMeasureFunc", None)
    if callable(unset):
        unset()
    free_recursive = getattr(node, "free_recursive", None) or getattr(node, "freeRecursive", None)
    if callable(free_recursive):
        free_recursive()
        return
    free = getattr(node, "free", None)
    if callable(free):
        free()


def loadPackageJson() -> dict[str, str]:
    package_json = Path(__file__).resolve().parents[2] / "package.json"
    if package_json.exists():
        parsed = json.loads(package_json.read_text())
        return {
            "name": parsed.get("name", "pyinkcli"),
            "version": parsed.get("version", "0.1.0"),
        }
    return {"name": "pyinkcli", "version": "0.1.0"}


packageInfo = loadPackageJson()


def getReconciler(root_node: Optional[DOMElement] = None) -> _Reconciler:
    """
    Get or create the reconciler instance.

    Args:
        root_node: Optional root node for a new reconciler.

    Returns:
        The Reconciler instance.
    """
    global _reconciler_instance
    if _reconciler_instance is None and root_node is not None:
        _reconciler_instance = _Reconciler(root_node)
    return _reconciler_instance


def createReconciler(root_node: DOMElement) -> _Reconciler:
    """
    Create a new reconciler instance.

    Args:
        root_node: The root DOM element.

    Returns:
        A new Reconciler instance.
    """
    return _Reconciler(root_node)


def batchedUpdates(callback: Callable[[], Any]) -> Any:
    """Module-level compatibility helper mirroring JS reconciler surface."""
    return _batched_updates_runtime(callback)


def discreteUpdates(callback: Callable[[], Any]) -> Any:
    """Module-level compatibility helper mirroring JS reconciler surface."""
    return _discrete_updates_runtime(callback)


def consumePendingRerenderPriority() -> Optional[UpdatePriority]:
    """Compatibility bridge for consuming queued rerender priority."""
    return _consume_pending_rerender_priority()
