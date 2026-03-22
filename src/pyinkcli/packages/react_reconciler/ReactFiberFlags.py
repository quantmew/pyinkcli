"""Fiber flag constants."""

from __future__ import annotations

NoFlags = 0
PerformedWork = 1 << 0
Placement = 1 << 1
Update = 1 << 2
Cloned = 1 << 3
ChildDeletion = 1 << 4
ContentReset = 1 << 5
Callback = 1 << 6
ForceClientRender = 1 << 7
Ref = 1 << 8
Snapshot = 1 << 9
Passive = 1 << 10
Visibility = 1 << 11
StoreConsistency = 1 << 12
Insertion = 1 << 13

Hydrate = Callback
ScheduleRetry = StoreConsistency
ShouldSuspendCommit = Visibility
ViewTransitionNamedMount = ShouldSuspendCommit
DidDefer = ContentReset
FormReset = Snapshot
AffectedParentLayout = ContentReset

LifecycleEffectMask = Passive | Update | Callback | Ref | Snapshot | StoreConsistency
HostEffectMask = (
    PerformedWork
    | Placement
    | Update
    | Cloned
    | ChildDeletion
    | ContentReset
    | Callback
    | ForceClientRender
    | Ref
    | Snapshot
    | Passive
    | Visibility
    | StoreConsistency
)

Incomplete = 1 << 14
ShouldCapture = 1 << 15
ForceUpdateForLegacySuspense = 1 << 16
DidPropagateContext = 1 << 17
NeedsPropagation = 1 << 18

Forked = 1 << 19
SnapshotStatic = 1 << 20
LayoutStatic = 1 << 21
RefStatic = LayoutStatic
PassiveStatic = 1 << 22
MaySuspendCommit = 1 << 23
ViewTransitionNamedStatic = SnapshotStatic | MaySuspendCommit
ViewTransitionStatic = 1 << 24
PortalStatic = 1 << 25
PlacementDEV = 1 << 26
MountLayoutDev = 1 << 27
MountPassiveDev = 1 << 28

BeforeMutationMask = Snapshot | Update
BeforeAndAfterMutationTransitionMask = Snapshot | Update | Placement | ChildDeletion | Visibility | ContentReset
MutationMask = Placement | Update | ChildDeletion | ContentReset | Ref | Visibility | FormReset
LayoutMask = Update | Callback | Ref | Visibility
PassiveMask = Passive | Visibility | ChildDeletion
PassiveTransitionMask = PassiveMask | Update | Placement
StaticMask = (
    LayoutStatic
    | PassiveStatic
    | RefStatic
    | MaySuspendCommit
    | ViewTransitionStatic
    | ViewTransitionNamedStatic
    | PortalStatic
    | Forked
)

__all__ = [name for name in globals() if name[0].isupper()]

