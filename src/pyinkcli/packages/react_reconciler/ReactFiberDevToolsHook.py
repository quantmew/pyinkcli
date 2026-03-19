"""DevTools hook surface aligned with ReactFiberDevToolsHook responsibilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler


def injectIntoDevTools(reconciler: "_Reconciler", package_info: dict[str, str]) -> bool:
    """Register the renderer with the devtools bridge."""
    from pyinkcli.packages.react_devtools_core.backend import createBackend, initializeBackend
    from pyinkcli.packages.react_devtools_core.window_polyfill import installDevtoolsWindowPolyfill

    if not initializeBackend():
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
        "getDisplayNameForNode": reconciler.getDisplayNameForNode,
        "getTreeSnapshot": reconciler.getTreeSnapshot,
        "getRootID": lambda: reconciler._devtools_tree_snapshot["rootID"],
        "inspectElement": reconciler.inspectElement,
        "inspectScreen": reconciler.inspectScreen,
        "getSerializedElementValueByPath": reconciler.getSerializedElementValueByPath,
        "getElementValueByPath": reconciler.getElementValueByPath,
        "getElementAttributeByPath": reconciler.getElementAttributeByPath,
        "getProfilingData": reconciler.getProfilingData,
        "getPathForElement": reconciler.getPathForElement,
        "getOwnersList": reconciler.getOwnersList,
        "getElementIDForHostInstance": reconciler.getElementIDForHostInstance,
        "getSuspenseNodeIDForHostInstance": reconciler.getSuspenseNodeIDForHostInstance,
        "overrideError": reconciler.overrideError,
        "overrideSuspense": reconciler.overrideSuspense,
        "overrideSuspenseMilestone": reconciler.overrideSuspenseMilestone,
        "overrideProps": reconciler.overrideProps,
        "overridePropsDeletePath": reconciler.overridePropsDeletePath,
        "overridePropsRenamePath": reconciler.overridePropsRenamePath,
        "overrideHookState": reconciler.overrideHookState,
        "overrideHookStateDeletePath": reconciler.overrideHookStateDeletePath,
        "overrideHookStateRenamePath": reconciler.overrideHookStateRenamePath,
        "overrideValueAtPath": reconciler.overrideValueAtPath,
        "deletePath": reconciler.deletePath,
        "renamePath": reconciler.renamePath,
        "scheduleUpdate": reconciler.scheduleUpdate,
        "scheduleRetry": reconciler.scheduleRetry,
        "clearErrorsAndWarnings": reconciler.clearErrorsAndWarnings,
        "clearErrorsForElementID": reconciler.clearErrorsForElementID,
        "clearWarningsForElementID": reconciler.clearWarningsForElementID,
        "copyElementPath": reconciler.copyElementPath,
        "storeAsGlobal": reconciler.storeAsGlobal,
        "getLastCopiedValue": reconciler.getLastCopiedValue,
        "getLastLoggedElement": reconciler.getLastLoggedElement,
        "getTrackedPath": reconciler.getTrackedPath,
        "getStoredGlobals": reconciler.getStoredGlobals,
        "getBackendNotificationLog": reconciler.getBackendNotificationLog,
        "logElementToConsole": reconciler.logElementToConsole,
        "setTrackedPath": reconciler.setTrackedPath,
    }
    renderer_interface["backend"] = createBackend(renderer_interface)
    renderer_interface["dispatchBridgeMessage"] = renderer_interface["backend"][
        "dispatchBridgeMessage"
    ]
    global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"] = renderer_interface
    global_scope["__INK_DEVTOOLS_RENDERERS__"][id(reconciler)] = renderer_interface
    return True


__all__ = ["injectIntoDevTools"]
