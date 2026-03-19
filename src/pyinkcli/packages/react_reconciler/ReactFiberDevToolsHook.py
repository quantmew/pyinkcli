"""DevTools hook surface aligned with ReactFiberDevToolsHook responsibilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyinkcli.devtools import createDevtoolsBackendFacade, initializeDevtools
from pyinkcli.devtools_window_polyfill import installDevtoolsWindowPolyfill

if TYPE_CHECKING:
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler


def injectIntoDevTools(reconciler: "_Reconciler", package_info: dict[str, str]) -> bool:
    """Register the renderer with the devtools bridge."""
    if not initializeDevtools():
        return False

    global_scope = installDevtoolsWindowPolyfill()
    renderer_interface: dict[str, Any] = {
        "bundleType": 1,
        "version": package_info["version"],
        "rendererPackageName": package_info["name"],
        "reconcilerVersion": package_info["version"],
        "rendererID": id(reconciler),
        "rendererConfig": {
            "supportsClassComponents": True,
            "supportsErrorBoundaries": True,
            "supportsCommitPhaseErrorRecovery": True,
        },
        "supportsTogglingSuspense": True,
        "getDisplayNameForNode": reconciler.getDevtoolsDisplayName,
        "getDisplayNameForElementID": reconciler.getDevtoolsDisplayName,
        "getTreeSnapshot": reconciler.getDevtoolsTreeSnapshot,
        "getRootID": lambda: reconciler._devtools_tree_snapshot["rootID"],
        "inspectElement": reconciler.inspectDevtoolsElement,
        "inspectScreen": reconciler.inspectDevtoolsScreen,
        "getSerializedElementValueByPath": reconciler.getSerializedDevtoolsElementValueByPath,
        "getElementValueByPath": reconciler.getDevtoolsElementValueByPath,
        "getElementAttributeByPath": reconciler.getDevtoolsElementAttributeByPath,
        "getProfilingData": reconciler.getDevtoolsProfilingData,
        "getPathForElement": reconciler.getDevtoolsPathForElement,
        "getOwnersList": reconciler.getDevtoolsOwnersList,
        "getElementIDForHostInstance": reconciler.getDevtoolsElementIDForHostInstance,
        "getSuspenseNodeIDForHostInstance": reconciler.getDevtoolsSuspenseNodeIDForHostInstance,
        "overrideError": reconciler.overrideDevtoolsError,
        "overrideSuspense": reconciler.overrideDevtoolsSuspense,
        "overrideSuspenseMilestone": reconciler.overrideDevtoolsSuspenseMilestone,
        "overrideProps": reconciler.overrideDevtoolsProps,
        "overridePropsDeletePath": reconciler.deleteDevtoolsPropsPath,
        "overridePropsRenamePath": reconciler.renameDevtoolsPropsPath,
        "overrideHookState": reconciler.overrideDevtoolsHookState,
        "overrideHookStateDeletePath": reconciler.deleteDevtoolsHookStatePath,
        "overrideHookStateRenamePath": reconciler.renameDevtoolsHookStatePath,
        "overrideValueAtPath": reconciler.overrideDevtoolsValueAtPath,
        "deletePath": reconciler.deleteDevtoolsPath,
        "renamePath": reconciler.renameDevtoolsPath,
        "scheduleUpdate": reconciler.scheduleDevtoolsUpdate,
        "scheduleRetry": reconciler.scheduleDevtoolsRetry,
        "clearErrorsAndWarnings": reconciler.clearDevtoolsErrorsAndWarnings,
        "clearErrorsForElementID": reconciler.clearDevtoolsErrorsForElement,
        "clearWarningsForElementID": reconciler.clearDevtoolsWarningsForElement,
        "copyElementPath": reconciler.copyDevtoolsElementPath,
        "storeAsGlobal": reconciler.storeDevtoolsValueAsGlobal,
        "getLastCopiedValue": reconciler.getDevtoolsLastCopiedValue,
        "getLastLoggedElement": reconciler.getDevtoolsLastLoggedElement,
        "getTrackedPath": reconciler.getDevtoolsTrackedPath,
        "getStoredGlobals": reconciler.getDevtoolsStoredGlobals,
        "getBackendNotificationLog": reconciler.getDevtoolsBackendNotificationLog,
        "logElementToConsole": reconciler.logDevtoolsElementToConsole,
        "setTrackedPath": reconciler.setDevtoolsTrackedPath,
    }
    renderer_interface["backendFacade"] = createDevtoolsBackendFacade(renderer_interface)
    renderer_interface["dispatchBridgeMessage"] = renderer_interface["backendFacade"]["dispatchMessage"]
    global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"] = renderer_interface
    global_scope["__INK_DEVTOOLS_RENDERERS__"][id(reconciler)] = renderer_interface
    return True


__all__ = ["injectIntoDevTools"]

