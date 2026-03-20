"""Command-facing reconciler composition methods."""

from __future__ import annotations

from typing import Any

from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    clearDevtoolsErrorsAndWarnings as _clear_devtools_errors_and_warnings,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    clearDevtoolsErrorsForElement as _clear_devtools_errors_for_element,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    clearDevtoolsWarningsForElement as _clear_devtools_warnings_for_element,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    copyDevtoolsElementPath as _copy_devtools_element_path,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    deleteDevtoolsHookStatePath as _delete_devtools_hook_state_path,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    deleteDevtoolsPath as _delete_devtools_path,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    deleteDevtoolsPropsPath as _delete_devtools_props_path,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    deleteDevtoolsStatePath as _delete_devtools_state_path,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    getDevtoolsBackendNotificationLog as _get_devtools_backend_notification_log,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    getDevtoolsLastCopiedValue as _get_devtools_last_copied_value,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    getDevtoolsLastLoggedElement as _get_devtools_last_logged_element,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    getDevtoolsMutableProps as _get_devtools_mutable_props_impl,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    getDevtoolsStoredGlobals as _get_devtools_stored_globals,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    getDevtoolsTrackedPath as _get_devtools_tracked_path,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    logDevtoolsElementToConsole as _log_devtools_element_to_console,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    overrideDevtoolsError as _override_devtools_error,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    overrideDevtoolsHookState as _override_devtools_hook_state,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    overrideDevtoolsProps as _override_devtools_props,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    overrideDevtoolsState as _override_devtools_state,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    overrideDevtoolsSuspense as _override_devtools_suspense,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    overrideDevtoolsSuspenseMilestone as _override_devtools_suspense_milestone,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    overrideDevtoolsValueAtPath as _override_devtools_value_at_path,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    recordDevtoolsBackendNotification as _record_devtools_backend_notification_impl,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    renameDevtoolsHookStatePath as _rename_devtools_hook_state_path,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    renameDevtoolsPath as _rename_devtools_path,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    renameDevtoolsPropsPath as _rename_devtools_props_path,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    renameDevtoolsStatePath as _rename_devtools_state_path,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    scheduleDevtoolsRetry as _schedule_devtools_retry,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    scheduleDevtoolsUpdate as _schedule_devtools_update,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    setDevtoolsTrackedPath as _set_devtools_tracked_path,
)
from pyinkcli.packages.react_reconciler.ReactFiberDevToolsCommands import (
    storeDevtoolsValueAsGlobal as _store_devtools_value_as_global,
)
from pyinkcli.packages.react_reconciler.ReactFiberReconcilerState import (
    createDevtoolsForcedError as _create_devtools_forced_error_impl,
)
from pyinkcli.packages.react_reconciler.ReactFiberReconcilerState import (
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
        renderer_id: int | None = None,
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
        hook_id: int | None,
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
        hook_id: int | None,
        path: list[Any],
    ) -> bool:
        return _delete_devtools_path(self, value_type, node_id, hook_id, path)

    def renamePath(
        self,
        value_type: str,
        node_id: str,
        hook_id: int | None,
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
        renderer_id: int | None = None,
    ) -> bool:
        return _clear_devtools_errors_and_warnings(self, renderer_id=renderer_id)

    def clearErrorsForElementID(
        self,
        id: str,
        renderer_id: int | None = None,
    ) -> bool:
        return _clear_devtools_errors_for_element(self, id, renderer_id=renderer_id)

    def clearWarningsForElementID(
        self,
        id: str,
        renderer_id: int | None = None,
    ) -> bool:
        return _clear_devtools_warnings_for_element(self, id, renderer_id=renderer_id)

    def copyElementPath(
        self,
        id: str,
        path: list[Any],
        renderer_id: int | None = None,
    ) -> str | None:
        return _copy_devtools_element_path(self, id, path, renderer_id=renderer_id)

    def storeAsGlobal(
        self,
        id: str,
        path: list[Any],
        count: int,
        renderer_id: int | None = None,
    ) -> str | None:
        return _store_devtools_value_as_global(
            self,
            id,
            path,
            count,
            renderer_id=renderer_id,
        )

    def getLastCopiedValue(self) -> str | None:
        return _get_devtools_last_copied_value(self)

    def getLastLoggedElement(self) -> dict[str, Any] | None:
        return _get_devtools_last_logged_element(self)

    def getTrackedPath(self) -> list[dict[str, Any]] | None:
        return _get_devtools_tracked_path(self)

    def getStoredGlobals(self) -> dict[str, Any]:
        return _get_devtools_stored_globals(self)

    def getBackendNotificationLog(self) -> list[dict[str, Any]]:
        return _get_devtools_backend_notification_log(self)

    def logElementToConsole(
        self,
        id: str,
        renderer_id: int | None = None,
    ) -> bool:
        return _log_devtools_element_to_console(self, id, renderer_id=renderer_id)

    def setTrackedPath(
        self,
        path: list[dict[str, Any]] | None,
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

    def _get_mutable_props(self, node_id: str) -> dict[str, Any] | None:
        return _get_devtools_mutable_props_impl(self, node_id)

    def _record_backend_notification(
        self,
        event: str,
        *,
        renderer_id: int | None = None,
        node_id: str | None = None,
        path: list[Any] | None = None,
        count: int | None = None,
        copied_value: str | None = None,
        global_key: str | None = None,
        suspended_set: list[Any] | None = None,
        normalized_suspended_set: list[Any] | None = None,
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
        hook_id: int | None,
        path: list[Any],
    ) -> list[Any] | None:
        return _normalize_hook_edit_path_impl(self, hook_id, path)

    def _create_devtools_forced_error(self) -> Exception:
        return _create_devtools_forced_error_impl()


__all__ = ["ReactFiberReconcilerCommands"]
