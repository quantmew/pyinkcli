"""Class component composition methods for the reconciler."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from pyinkcli._component_runtime import _Component, isElement
from pyinkcli.packages.ink.dom import DOMElement
from pyinkcli.packages.react_reconciler.ReactFiberClassComponent import (
    applyErrorBoundaryState as _apply_error_boundary_state_impl,
    captureCommitPhaseError as _capture_commit_phase_error_impl,
    cleanupClassComponentInstances as _cleanup_class_component_instances_impl,
    disposeStaleClassComponentInstances as _dispose_stale_class_component_instances_impl,
    flushClassComponentCommitCallbacks as _flush_class_component_commit_callbacks_impl,
    flushComponentDidCatchCallbacks as _flush_component_did_catch_callbacks_impl,
    getOrCreateClassComponentInstance as _get_or_create_class_component_instance_impl,
    invokeComponentDidMount as _invoke_component_did_mount_impl,
    invokeComponentDidUpdate as _invoke_component_did_update_impl,
    isErrorBoundary as _is_error_boundary_impl,
    reconcileClassComponent as _reconcile_class_component_impl,
    renderErrorBoundaryFallback as _render_error_boundary_fallback_impl,
    scheduleClassComponentCommitCallback as _schedule_class_component_commit_callback_impl,
    unmountClassComponentInstance as _unmount_class_component_instance_impl,
)
from pyinkcli.packages.react_reconciler.ReactFiberReconcilerState import (
    getComponentDisplayName as _get_component_display_name_impl,
    getComponentInstanceID as _get_component_instance_id_impl,
    isComponentTypeErrorBoundary as _is_component_type_error_boundary_impl,
)

if TYPE_CHECKING:
    from pyinkcli.component import RenderableNode


class ReactFiberReconcilerClassComponent:
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
        return _reconcile_class_component_impl(
            self,
            component_type=component_type,
            component_id=component_id,
            props=props,
            children=children,
            parent=parent,
            path=path,
            dom_index=dom_index,
            devtools_parent_id=devtools_parent_id,
            vnode_key=vnode_key,
            owner_entry=owner_entry,
        )

    def _get_component_instance_id(
        self,
        component_type: Any,
        vnode: "RenderableNode",
        path: tuple[Any, ...],
    ) -> str:
        assert isElement(vnode)
        return _get_component_instance_id_impl(self, component_type, vnode, path)

    def _get_component_display_name(self, component_type: Any) -> str:
        return _get_component_display_name_impl(self, component_type)

    def _is_component_type_error_boundary(self, component_type: type[_Component]) -> bool:
        return _is_component_type_error_boundary_impl(self, component_type)

    def _get_or_create_class_component_instance(
        self,
        component_type: type[_Component],
        component_id: str,
        children: tuple["RenderableNode", ...],
        props: dict[str, Any],
    ) -> tuple[_Component, bool, dict[str, Any], dict[str, Any]]:
        return _get_or_create_class_component_instance_impl(
            self,
            component_type,
            component_id,
            children,
            props,
        )

    def _schedule_class_component_commit_callback(
        self,
        instance: _Component,
        *,
        is_new_instance: bool,
        should_update: bool,
        previous_props: dict[str, Any],
        previous_state: dict[str, Any],
    ) -> None:
        _schedule_class_component_commit_callback_impl(
            self,
            instance,
            is_new_instance=is_new_instance,
            should_update=should_update,
            previous_props=previous_props,
            previous_state=previous_state,
        )

    def _invoke_component_did_mount(self, instance: _Component) -> None:
        _invoke_component_did_mount_impl(self, instance)

    def _invoke_component_did_update(
        self,
        instance: _Component,
        previous_props: dict[str, Any],
        previous_state: dict[str, Any],
    ) -> None:
        _invoke_component_did_update_impl(
            self,
            instance,
            previous_props,
            previous_state,
        )

    def _flush_class_component_commit_callbacks(self) -> bool:
        return _flush_class_component_commit_callbacks_impl(self)

    def cleanup_class_component_instances(self) -> None:
        _cleanup_class_component_instances_impl(self)

    def _dispose_stale_class_component_instances(self) -> None:
        _dispose_stale_class_component_instances_impl(self)

    def _unmount_class_component_instance(self, instance: _Component) -> None:
        _unmount_class_component_instance_impl(self, instance)

    def _capture_commit_phase_error(
        self,
        instance: _Component,
        error: Exception,
    ) -> bool:
        return _capture_commit_phase_error_impl(self, instance, error)

    def _is_error_boundary(
        self,
        component_type: type[_Component],
        instance: _Component,
    ) -> bool:
        return _is_error_boundary_impl(self, component_type, instance)

    def _render_error_boundary_fallback(
        self,
        component_type: type[_Component],
        instance: _Component,
        error: Exception,
    ) -> "RenderableNode":
        return _render_error_boundary_fallback_impl(
            self,
            component_type,
            instance,
            error,
        )

    def _apply_error_boundary_state(
        self,
        component_type: type[_Component],
        instance: _Component,
        error: Exception,
    ) -> None:
        _apply_error_boundary_state_impl(self, component_type, instance, error)

    def _flush_component_did_catch_callbacks(self, *, include_deferred: bool) -> None:
        _flush_component_did_catch_callbacks_impl(
            self,
            include_deferred=include_deferred,
        )


__all__ = ["ReactFiberReconcilerClassComponent"]
