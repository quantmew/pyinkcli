"""Inspection-facing reconciler composition methods."""

from __future__ import annotations

from typing import Any, Callable, Optional

from pyinkcli.packages.react_reconciler.ReactChildFiber import (
    appendDevtoolsNode as _append_devtools_node_impl,
    buildDevtoolsNodeID as _build_devtools_node_id_impl,
)
from pyinkcli.packages.react_reconciler.ReactFiberComponentStack import (
    buildDevtoolsStack as _build_devtools_stack,
    getCurrentOwnerSource as _get_current_owner_source,
    getSourceForTarget as _get_source_for_target,
    makeCallSite as _make_call_site,
    serializeDevtoolsOwnerStack as _serialize_devtools_owner_stack,
)
from pyinkcli.packages.react_reconciler.ReactFiberContainerUpdate import (
    getEffectiveDevtoolsProps as _get_effective_devtools_props_impl,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsInspection import (
    buildDevtoolsFingerprint as _build_devtools_fingerprint,
    cleanDevtoolsInspectedElementForBridge as _clean_devtools_inspected_element_for_bridge,
    cleanDevtoolsValueForBridge as _clean_devtools_value_for_bridge,
    cloneDevtoolsValue as _clone_devtools_value,
    deleteNestedValue as _delete_nested_value,
    finalizeDevtoolsTreeSnapshot as _finalize_devtools_tree_snapshot,
    fingerprintDevtoolsValue as _fingerprint_devtools_value_impl,
    getDevtoolsElementValueByPath as _get_devtools_element_value_by_path,
    getNestedValue as _get_nested_value,
    getSerializedDevtoolsElementValueByPath as _get_serialized_devtools_element_value_by_path,
    inspectDevtoolsElement as _inspect_devtools_element,
    popNestedValue as _pop_nested_value,
    recordDevtoolsInspectedElement as _record_devtools_inspected_element,
    setNestedValue as _set_nested_value,
)
from pyinkcli.packages.react_reconciler.ReactFiberTreeReflection import (
    findNearestDevtoolsAncestor as _find_nearest_devtools_ancestor_impl,
    getDevtoolsDisplayName as _get_devtools_display_name_impl,
    getDevtoolsElementIDForHostInstance as _get_devtools_element_id_for_host_instance_impl,
    getDevtoolsNode as _get_devtools_node_impl,
    getDevtoolsOwnersList as _get_devtools_owners_list_impl,
    getDevtoolsPathForElement as _get_devtools_path_for_element_impl,
    getDevtoolsProfilingData as _get_devtools_profiling_data_impl,
    getDevtoolsSuspenseNodeIDForHostInstance as _get_devtools_suspense_node_id_for_host_instance_impl,
    getDevtoolsTreeSnapshot as _get_devtools_tree_snapshot_impl,
    hasDevtoolsNode as _has_devtools_node_impl,
    isMostRecentlyInspectedElement as _is_most_recently_inspected_element_impl,
    mergeDevtoolsInspectedPath as _merge_devtools_inspected_path_impl,
)


class ReactFiberReconcilerInspection:
    def getTreeSnapshot(self) -> dict[str, Any]:
        return _get_devtools_tree_snapshot_impl(self)

    def getDisplayNameForNode(self, node_id: str) -> Optional[str]:
        return _get_devtools_display_name_impl(self, node_id)

    def inspectElement(
        self,
        request_id: int,
        node_id: str,
        inspected_paths: Optional[Any] = None,
        force_full_data: bool = False,
    ) -> dict[str, Any]:
        return _inspect_devtools_element(
            self,
            request_id,
            node_id,
            inspected_paths=inspected_paths,
            force_full_data=force_full_data,
        )

    def inspectScreen(
        self,
        request_id: int,
        node_id: Optional[str] = None,
        path: Optional[Any] = None,
        force_full_data: bool = False,
        renderer_id: Optional[int] = None,
    ) -> dict[str, Any]:
        del renderer_id
        screen_id = node_id or self._devtools_tree_snapshot.get("rootID", "root")
        return self.inspectElement(
            request_id,
            screen_id,
            inspected_paths=path,
            force_full_data=force_full_data,
        )

    def getSerializedElementValueByPath(
        self,
        node_id: str,
        path: list[Any],
    ) -> Optional[str]:
        return _get_serialized_devtools_element_value_by_path(self, node_id, path)

    def getElementValueByPath(
        self,
        node_id: str,
        path: list[Any],
    ) -> Any:
        return _get_devtools_element_value_by_path(self, node_id, path)

    def getElementAttributeByPath(
        self,
        node_id: str,
        path: list[Any],
    ) -> Any:
        return self.getElementValueByPath(node_id, path)

    def getProfilingData(self) -> dict[str, Any]:
        return _get_devtools_profiling_data_impl(self)

    def getPathForElement(
        self,
        node_id: str,
    ) -> Optional[list[dict[str, Any]]]:
        return _get_devtools_path_for_element_impl(self, node_id)

    def getOwnersList(
        self,
        node_id: str,
    ) -> list[dict[str, Any]]:
        return _get_devtools_owners_list_impl(self, node_id)

    def getElementIDForHostInstance(
        self,
        target: Any,
    ) -> Optional[str]:
        return _get_devtools_element_id_for_host_instance_impl(self, target)

    def getSuspenseNodeIDForHostInstance(
        self,
        target: Any,
    ) -> Optional[str]:
        return _get_devtools_suspense_node_id_for_host_instance_impl(self, target)

    def _has_tree_node(self, node_id: str) -> bool:
        return _has_devtools_node_impl(self, node_id)

    def _is_most_recently_inspected(self, node_id: str) -> bool:
        return _is_most_recently_inspected_element_impl(self, node_id)

    def _merge_inspected_path(self, path: list[Any]) -> None:
        _merge_devtools_inspected_path_impl(self, path)

    def _get_tree_node(self, node_id: str) -> Optional[dict[str, Any]]:
        return _get_devtools_node_impl(self, node_id)

    def _find_nearest_tree_ancestor(
        self,
        node_id: str,
        *,
        predicate: Callable[[dict[str, Any]], bool],
    ) -> Optional[str]:
        return _find_nearest_devtools_ancestor_impl(
            self,
            node_id,
            predicate=predicate,
        )

    def _clone_inspected_value(self, value: Any) -> Any:
        return _clone_devtools_value(self, value)

    def _fingerprint_inspected_value(self, value: Any) -> Any:
        return _fingerprint_devtools_value_impl(self, value)

    def _build_inspected_fingerprint(self, value: Any) -> str:
        return _build_devtools_fingerprint(self, value)

    def _clean_value_for_bridge(
        self,
        value: Any,
        *,
        root_key: str,
        path: list[Any],
        lookup_path: Optional[list[Any]] = None,
    ) -> dict[str, Any]:
        return _clean_devtools_value_for_bridge(
            self,
            value,
            root_key=root_key,
            path=path,
            lookup_path=lookup_path,
        )

    def _clean_inspected_element_for_bridge(
        self,
        element: dict[str, Any],
    ) -> dict[str, Any]:
        return _clean_devtools_inspected_element_for_bridge(self, element)

    def _get_nested_value(
        self,
        target: Any,
        path: list[Any],
    ) -> tuple[Any, bool]:
        return _get_nested_value(self, target, path)

    def _set_nested_value(self, target: Any, path: list[Any], value: Any) -> bool:
        return _set_nested_value(self, target, path, value)

    def _delete_nested_value(self, target: dict[str, Any], path: list[Any]) -> bool:
        return _delete_nested_value(self, target, path)

    def _pop_nested_value(self, target: dict[str, Any], path: list[Any]) -> tuple[Any, bool]:
        return _pop_nested_value(self, target, path)

    def _build_tree_node_id(
        self,
        display_name: str,
        path: tuple[Any, ...],
        key: Optional[str],
    ) -> str:
        return _build_devtools_node_id_impl(self, display_name, path, key)

    _build_devtools_node_id = _build_tree_node_id

    def _append_tree_node(
        self,
        *,
        node_id: str,
        parent_id: str,
        display_name: str,
        element_type: str,
        key: Optional[str],
        is_error_boundary: bool,
    ) -> str:
        return _append_devtools_node_impl(
            self,
            node_id=node_id,
            parent_id=parent_id,
            display_name=display_name,
            element_type=element_type,
            key=key,
            is_error_boundary=is_error_boundary,
        )

    def _record_inspected_element(
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
        _record_devtools_inspected_element(
            self,
            node_id=node_id,
            element_type=element_type,
            key=key,
            props=props,
            state=state,
            hooks=hooks,
            context=context,
            can_edit_hooks=can_edit_hooks,
            can_edit_function_props=can_edit_function_props,
            can_toggle_error=can_toggle_error,
            is_errored=is_errored,
            can_toggle_suspense=can_toggle_suspense,
            is_suspended=is_suspended,
            nearest_error_boundary_id=nearest_error_boundary_id,
            nearest_suspense_boundary_id=nearest_suspense_boundary_id,
            owners=owners,
            source=source,
            stack=stack,
            suspended_by=suspended_by,
        )

    def _get_source_for_target(
        self,
        target: Any,
        display_name: str,
    ) -> Optional[list[Any]]:
        return _get_source_for_target(self, target, display_name)

    def _make_call_site(
        self,
        display_name: str,
        source: Optional[list[Any]],
    ) -> Optional[list[Any]]:
        return _make_call_site(self, display_name, source)

    def _serialize_owner_stack(self) -> Optional[list[dict[str, Any]]]:
        return _serialize_devtools_owner_stack(self)

    def _build_owner_stack(
        self,
        entries: list[dict[str, Any]],
        *,
        current_entry: Optional[dict[str, Any]] = None,
    ) -> Optional[list[list[Any]]]:
        return _build_devtools_stack(self, entries, current_entry=current_entry)

    def _get_current_owner_source(self) -> Optional[list[Any]]:
        return _get_current_owner_source(self)

    def _finalize_tree_snapshot(self) -> None:
        _finalize_devtools_tree_snapshot(self)

    def _get_effective_props(
        self,
        node_id: str,
        props: dict[str, Any],
    ) -> dict[str, Any]:
        return _get_effective_devtools_props_impl(self, node_id, props)


__all__ = ["ReactFiberReconcilerInspection"]
