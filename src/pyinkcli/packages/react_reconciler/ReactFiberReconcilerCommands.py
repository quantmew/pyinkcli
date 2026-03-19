"""Command-facing reconciler composition methods."""

from __future__ import annotations

from typing import Any, Optional

from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    clearDevtoolsErrorsAndWarnings as _clear_devtools_errors_and_warnings,
    clearDevtoolsErrorsForElement as _clear_devtools_errors_for_element,
    clearDevtoolsWarningsForElement as _clear_devtools_warnings_for_element,
    copyDevtoolsElementPath as _copy_devtools_element_path,
    deleteDevtoolsHookStatePath as _delete_devtools_hook_state_path,
    deleteDevtoolsPath as _delete_devtools_path,
    deleteDevtoolsPropsPath as _delete_devtools_props_path,
    deleteDevtoolsStatePath as _delete_devtools_state_path,
    getDevtoolsBackendNotificationLog as _get_devtools_backend_notification_log,
    getDevtoolsLastCopiedValue as _get_devtools_last_copied_value,
    getDevtoolsLastLoggedElement as _get_devtools_last_logged_element,
    getDevtoolsMutableProps as _get_devtools_mutable_props_impl,
    getDevtoolsStoredGlobals as _get_devtools_stored_globals,
    getDevtoolsTrackedPath as _get_devtools_tracked_path,
    logDevtoolsElementToConsole as _log_devtools_element_to_console,
    overrideDevtoolsError as _override_devtools_error,
    overrideDevtoolsHookState as _override_devtools_hook_state,
    overrideDevtoolsProps as _override_devtools_props,
    overrideDevtoolsState as _override_devtools_state,
    overrideDevtoolsSuspense as _override_devtools_suspense,
    overrideDevtoolsSuspenseMilestone as _override_devtools_suspense_milestone,
    overrideDevtoolsValueAtPath as _override_devtools_value_at_path,
    recordDevtoolsBackendNotification as _record_devtools_backend_notification_impl,
    renameDevtoolsHookStatePath as _rename_devtools_hook_state_path,
    renameDevtoolsPath as _rename_devtools_path,
    renameDevtoolsPropsPath as _rename_devtools_props_path,
    renameDevtoolsStatePath as _rename_devtools_state_path,
    scheduleDevtoolsRetry as _schedule_devtools_retry,
    scheduleDevtoolsUpdate as _schedule_devtools_update,
    setDevtoolsTrackedPath as _set_devtools_tracked_path,
    storeDevtoolsValueAsGlobal as _store_devtools_value_as_global,
)
from pyinkcli.packages.react_reconciler.ReactFiberReconcilerState import (
    createDevtoolsForcedError as _create_devtools_forced_error_impl,
    normalizeHookEditPath as _normalize_hook_edit_path_impl,
)


class ReactFiberReconcilerCommands:
    def overrideProps(
        self,
        node_id: str,
        path: list[Any],
        value: Any,
    ) -> bool:
        return _override_devtools_props(self, node_id, path, value)

    def overrideError(self, node_id: str, force_error: bool) -> bool:
        return _override_devtools_error(self, node_id, force_error)

    def overrideSuspense(self, node_id: str, force_fallback: bool) -> bool:
        return _override_devtools_suspense(self, node_id, force_fallback)

    def overrideSuspenseMilestone(
        self,
        suspended_set: list[str],
        renderer_id: Optional[int] = None,
    ) -> bool:
        return _override_devtools_suspense_milestone(
            self,
            suspended_set,
            renderer_id=renderer_id,
        )

    def overridePropsDeletePath(
        self,
        node_id: str,
        path: list[Any],
    ) -> bool:
        return _delete_devtools_props_path(self, node_id, path)

    def overridePropsRenamePath(
        self,
        node_id: str,
        old_path: list[Any],
        new_path: list[Any],
    ) -> bool:
        return _rename_devtools_props_path(self, node_id, old_path, new_path)

    def overrideValueAtPath(
        self,
        value_type: str,
        node_id: str,
        hook_id: Optional[int],
        path: list[Any],
        value: Any,
    ) -> bool:
        return _override_devtools_value_at_path(
            self,
            value_type,
            node_id,
            hook_id,
            path,
            value,
        )

    def deletePath(
        self,
        value_type: str,
        node_id: str,
        hook_id: Optional[int],
        path: list[Any],
    ) -> bool:
        return _delete_devtools_path(self, value_type, node_id, hook_id, path)

    def renamePath(
        self,
        value_type: str,
        node_id: str,
        hook_id: Optional[int],
        old_path: list[Any],
        new_path: list[Any],
    ) -> bool:
        return _rename_devtools_path(
            self,
            value_type,
            node_id,
            hook_id,
            old_path,
            new_path,
        )

    def scheduleUpdate(self, node_id: str) -> bool:
        return _schedule_devtools_update(self, node_id)

    def scheduleRetry(self, node_id: str) -> bool:
        return _schedule_devtools_retry(self, node_id)

    def clearErrorsAndWarnings(
        self,
        renderer_id: Optional[int] = None,
    ) -> bool:
        return _clear_devtools_errors_and_warnings(self, renderer_id=renderer_id)

    def clearErrorsForElementID(
        self,
        id: str,
        renderer_id: Optional[int] = None,
    ) -> bool:
        return _clear_devtools_errors_for_element(self, id, renderer_id=renderer_id)

    def clearWarningsForElementID(
        self,
        id: str,
        renderer_id: Optional[int] = None,
    ) -> bool:
        return _clear_devtools_warnings_for_element(self, id, renderer_id=renderer_id)

    def copyElementPath(
        self,
        id: str,
        path: list[Any],
        renderer_id: Optional[int] = None,
    ) -> Optional[str]:
        return _copy_devtools_element_path(self, id, path, renderer_id=renderer_id)

    def storeAsGlobal(
        self,
        id: str,
        path: list[Any],
        count: int,
        renderer_id: Optional[int] = None,
    ) -> Optional[str]:
        return _store_devtools_value_as_global(
            self,
            id,
            path,
            count,
            renderer_id=renderer_id,
        )

    def getLastCopiedValue(self) -> Optional[str]:
        return _get_devtools_last_copied_value(self)

    def getLastLoggedElement(self) -> Optional[dict[str, Any]]:
        return _get_devtools_last_logged_element(self)

    def getTrackedPath(self) -> Optional[list[dict[str, Any]]]:
        return _get_devtools_tracked_path(self)

    def getStoredGlobals(self) -> dict[str, Any]:
        return _get_devtools_stored_globals(self)

    def getBackendNotificationLog(self) -> list[dict[str, Any]]:
        return _get_devtools_backend_notification_log(self)

    def logElementToConsole(
        self,
        id: str,
        renderer_id: Optional[int] = None,
    ) -> bool:
        return _log_devtools_element_to_console(self, id, renderer_id=renderer_id)

    def setTrackedPath(
        self,
        path: Optional[list[dict[str, Any]]],
    ) -> None:
        _set_devtools_tracked_path(self, path)

    def overrideHookState(
        self,
        node_id: str,
        path: list[Any],
        value: Any,
    ) -> bool:
        return _override_devtools_hook_state(self, node_id, path, value)

    def overrideHookStateDeletePath(
        self,
        node_id: str,
        path: list[Any],
    ) -> bool:
        return _delete_devtools_hook_state_path(self, node_id, path)

    def overrideHookStateRenamePath(
        self,
        node_id: str,
        old_path: list[Any],
        new_path: list[Any],
    ) -> bool:
        return _rename_devtools_hook_state_path(self, node_id, old_path, new_path)

    def overrideState(
        self,
        node_id: str,
        path: list[Any],
        value: Any,
    ) -> bool:
        return _override_devtools_state(self, node_id, path, value)

    def overrideStateDeletePath(
        self,
        node_id: str,
        path: list[Any],
    ) -> bool:
        return _delete_devtools_state_path(self, node_id, path)

    def overrideStateRenamePath(
        self,
        node_id: str,
        old_path: list[Any],
        new_path: list[Any],
    ) -> bool:
        return _rename_devtools_state_path(self, node_id, old_path, new_path)

    def _get_mutable_props(self, node_id: str) -> Optional[dict[str, Any]]:
        return _get_devtools_mutable_props_impl(self, node_id)

    def _record_backend_notification(
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
        _record_devtools_backend_notification_impl(
            self,
            event,
            renderer_id=renderer_id,
            node_id=node_id,
            path=path,
            count=count,
            copied_value=copied_value,
            global_key=global_key,
            suspended_set=suspended_set,
            normalized_suspended_set=normalized_suspended_set,
        )

    def _normalize_hook_edit_path(
        self,
        hook_id: Optional[int],
        path: list[Any],
    ) -> Optional[list[Any]]:
        return _normalize_hook_edit_path_impl(self, hook_id, path)

    def _create_devtools_forced_error(self) -> Exception:
        return _create_devtools_forced_error_impl()


__all__ = ["ReactFiberReconcilerCommands"]
