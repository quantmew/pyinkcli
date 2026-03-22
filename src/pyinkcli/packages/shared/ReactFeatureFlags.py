"""Feature flag defaults used by the compatibility layer."""

from __future__ import annotations

disableSchedulerTimeoutInWorkLoop = False
enableSuspenseCallback = False
enableScopeAPI = False
enableCreateEventHandleAPI = False
enableLegacyFBSupport = False
enableYieldingBeforePassive = False
enableThrottledScheduling = False
enableLegacyCache = False
enableAsyncIterableChildren = False
enableTaint = False
enableViewTransition = True
enableGestureTransition = False
enableScrollEndPolyfill = False
enableSuspenseyImages = False
enableFizzBlockingRender = False
enableSrcObject = False
enableHydrationChangeEvent = False
enableDefaultTransitionIndicator = False
enableOptimisticKey = False
enableObjectFiber = False
enableTransitionTracing = False
enableLegacyHidden = False
enableSuspenseAvoidThisFallback = False
enableCPUSuspense = False
enableNoCloningMemoCache = False
enableFizzExternalRuntime = False
alwaysThrottleRetries = True
enableEffectEventMutationPhase = False
passChildrenWhenCloningPersistedNodes = False
enableEagerAlternateStateNodeCleanup = True
enableRetryLaneExpiration = False
retryLaneExpirationMs = 5000
syncLaneExpirationMs = 250
transitionLaneExpirationMs = 5000
enableInfiniteRenderLoopDetection = False
enableFragmentRefs = True
enableFragmentRefsScrollIntoView = True
enableFragmentRefsInstanceHandles = False
enableFragmentRefsTextNodes = True
enableInternalInstanceMap = False
disableLegacyContext = True
disableLegacyContextForFunctionComponents = True
enableMoveBefore = False
disableClientCache = True
enableReactTestRendererWarning = True
disableLegacyMode = True
disableCommentsAsDOMContainers = True
enableTrustedTypesIntegration = True
disableInputAttributeSyncing = False
disableTextareaChildren = False
enableParallelTransitions = False
enableProfilerTimer = False
enableComponentPerformanceTrack = True
enablePerformanceIssueReporting = False
enableSchedulingProfiler = False
enableProfilerCommitHooks = False
enableProfilerNestedUpdatePhase = False
enableAsyncDebugInfo = True
enableUpdaterTracking = False
ownerStackLimit = 10_000

__all__ = [name for name in globals() if name.startswith("enable") or name.startswith("disable") or name.endswith("Limit") or name.endswith("Ms") or name == "alwaysThrottleRetries"]
