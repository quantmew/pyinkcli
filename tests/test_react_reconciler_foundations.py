from __future__ import annotations

from types import SimpleNamespace

import pyinkcli.packages.react_reconciler.ReactCurrentFiber as ReactCurrentFiber
from pyinkcli.packages.react_reconciler.ReactCurrentFiber import (
    getCurrentFiberOwnerNameInDevOrNull,
    resetCurrentFiber,
    runWithFiberInDEV,
    setCurrentFiber,
    setIsRendering,
)
from pyinkcli.packages.react_reconciler.ReactFiberBeginWork import (
    beginWork,
    checkIfWorkInProgressReceivedUpdate,
    resetWorkInProgressReceivedUpdate,
)
from pyinkcli.packages.react_reconciler.ReactFiberCompleteWork import (
    bubbleProperties,
    completeTree,
    completeWork,
)
from pyinkcli.packages.react_reconciler.ReactFiberConcurrentUpdates import (
    markUpdateLaneFromFiberToRoot,
)
from pyinkcli.packages.react_reconciler.ReactFiberLane import (
    DefaultLane,
    IdleLane,
    InputContinuousLane,
    NoLanes,
    SyncLane,
    TransitionLane1,
    getHighestPriorityLane,
    getLabelForLane,
    mergeLanes,
    removeLanes,
)
from pyinkcli.packages.react_reconciler.ReactFiberFlags import Update
from pyinkcli.packages.react_reconciler.ReactWorkTags import (
    ClassComponent,
    Fragment,
    HostComponent,
    HostRoot,
    HostText,
    SuspenseComponent,
)
from pyinkcli.packages.react_reconciler.ReactFiberHooks import (
    HooksDispatcherOnMount,
    HooksDispatcherOnUpdate,
    finishRenderingHooks,
    renderWithHooks,
)
from pyinkcli.packages.react_reconciler.ReactFiberWorkLoop import performWorkOnRoot
from pyinkcli.packages.react_reconciler.ReactFiberWorkLoop import (
    getWorkInProgressRoot,
    getWorkInProgressRootRenderLanes,
    getPendingPassiveEffectsLanes,
    getRootWithPendingPassiveEffects,
    flushPendingEffects,
    hasPendingCommitEffects,
)
from pyinkcli.packages.react_reconciler.ReactFiberNewContext import (
    checkIfContextChanged,
    finishReadingContext,
    popProvider,
    prepareToReadContext,
    pushProvider,
    readContext,
)
import pyinkcli.packages.react_reconciler.ReactFiberRootScheduler as RootScheduler
from pyinkcli.packages.react_reconciler.ReactHookEffectTags import (
    HasEffect,
    Insertion as HookInsertionTag,
    Layout as HookLayoutTag,
    Passive as HookPassiveTag,
)
from pyinkcli.packages.react_reconciler.ReactSharedInternals import shared_internals


def test_react_fiber_lane_helpers_choose_highest_priority_lane() -> None:
    lanes = mergeLanes(TransitionLane1, DefaultLane)
    lanes = mergeLanes(lanes, SyncLane)

    assert getHighestPriorityLane(lanes) == SyncLane
    assert removeLanes(lanes, SyncLane) == mergeLanes(TransitionLane1, DefaultLane)
    assert getLabelForLane(DefaultLane) == "Default"
    assert getHighestPriorityLane(NoLanes) == NoLanes


def test_react_current_fiber_updates_shared_internals_stack_provider() -> None:
    fiber = SimpleNamespace(element_type="SampleComponent", component_id="fiber-1")

    setCurrentFiber(fiber)
    setIsRendering(True)

    assert ReactCurrentFiber.current is fiber
    assert getCurrentFiberOwnerNameInDevOrNull() == "SampleComponent"
    assert callable(shared_internals.getCurrentStack)
    assert "SampleComponent" in shared_internals.getCurrentStack()

    resetCurrentFiber()

    assert shared_internals.getCurrentStack is None


def test_run_with_fiber_in_dev_restores_previous_current_fiber() -> None:
    previous = SimpleNamespace(element_type="Previous", component_id="prev")
    target = SimpleNamespace(element_type="Target", component_id="target")
    setCurrentFiber(previous)

    def reader() -> str | None:
        return getCurrentFiberOwnerNameInDevOrNull()

    assert runWithFiberInDEV(target, reader) == "Target"
    assert getCurrentFiberOwnerNameInDevOrNull() == "Previous"

    resetCurrentFiber()


def test_render_with_hooks_swaps_current_dispatcher_temporarily() -> None:
    previous_dispatcher = shared_internals.H
    fiber = SimpleNamespace(element_type="Hooked", component_id="hooked")
    observed: list[object] = []

    def component():
        observed.append(shared_internals.H)
        return "ok"

    assert renderWithHooks(fiber, component) == "ok"
    assert observed[0] in (HooksDispatcherOnMount, HooksDispatcherOnUpdate)
    assert observed[0] is not previous_dispatcher
    finishRenderingHooks()
    assert shared_internals.H is previous_dispatcher


def test_render_with_hooks_marks_received_update_when_props_change() -> None:
    previous_dispatcher = shared_internals.H
    resetWorkInProgressReceivedUpdate()
    fiber = SimpleNamespace(
        element_type="Hooked",
        component_id="hooked",
        pending_props={"value": "next"},
        memoized_props={"value": "prev"},
        alternate=SimpleNamespace(hook_head=object(), memoized_props={"value": "prev"}),
    )

    result = renderWithHooks(fiber, lambda *, value: value, value="next")

    assert result == "next"
    assert checkIfWorkInProgressReceivedUpdate() is True
    finishRenderingHooks()
    assert shared_internals.H is previous_dispatcher


def test_render_with_hooks_marks_received_update_when_context_changes() -> None:
    from pyinkcli.packages import react
    from pyinkcli.packages.react import useContext

    previous_dispatcher = shared_internals.H
    resetWorkInProgressReceivedUpdate()
    context = react.createContext("prev")
    reconciler = SimpleNamespace(_context_provider_stack=[])
    current = SimpleNamespace(
        hook_head=object(),
        memoized_props={"value": "same"},
        dependencies=[(context, "prev")],
    )
    fiber = SimpleNamespace(
        element_type="Hooked",
        component_id="hooked-context",
        pending_props={"value": "same"},
        memoized_props={"value": "same"},
        alternate=current,
        dependencies=[],
    )

    def component():
        return useContext(context)

    pushProvider(reconciler, context, "next")
    try:
        assert renderWithHooks(fiber, component) == "next"
        assert checkIfWorkInProgressReceivedUpdate() is True
        assert fiber.dependencies == [(context, "next")]
        finishRenderingHooks()
        assert shared_internals.H is previous_dispatcher
    finally:
        popProvider(reconciler, context)


def test_root_scheduler_tracks_and_flushes_scheduled_roots() -> None:
    RootScheduler.resetRootSchedule()
    flushed: list[str] = []

    class FakeReconciler:
        def flush_sync_work(self, container) -> None:
            flushed.append("flush")
            container.pending_updates = []
            container.pending_lanes = 0
            container.update_running = False

    container = SimpleNamespace(
        next=None,
        pending_updates=[("update", None)],
        pending_lanes=1,
        callback_priority=0,
        scheduled_callback_priority=0,
        update_running=False,
        _reconciler=FakeReconciler(),
    )

    RootScheduler.ensureRootIsScheduled(container)

    assert RootScheduler.firstScheduledRoot is container

    RootScheduler.flushSyncWorkOnAllRoots()

    assert flushed == ["flush"]
    assert RootScheduler.firstScheduledRoot is None
    assert container.next is None
    assert container.callback_priority == 0
    assert container.scheduled_callback_priority == 0


def test_root_scheduler_classifies_lane_families() -> None:
    assert RootScheduler.getRootLaneFamily(SimpleNamespace(pending_lanes=0)) == "idle"
    assert RootScheduler.getRootLaneFamily(SimpleNamespace(pending_lanes=SyncLane)) == "discrete"
    assert (
        RootScheduler.getRootLaneFamily(SimpleNamespace(pending_lanes=InputContinuousLane))
        == "continuous"
    )
    assert RootScheduler.getRootLaneFamily(SimpleNamespace(pending_lanes=DefaultLane)) == "default"
    assert (
        RootScheduler.getRootLaneFamily(SimpleNamespace(pending_lanes=TransitionLane1))
        == "transition"
    )
    assert RootScheduler.getRootLaneFamily(SimpleNamespace(pending_lanes=IdleLane)) == "idle"


def test_root_scheduler_schedule_mode_maps_lane_families_to_execution_modes() -> None:
    assert RootScheduler.getRootScheduleMode(SimpleNamespace(tag=1, pending_lanes=0)) == "idle"
    assert RootScheduler.getRootScheduleMode(SimpleNamespace(tag=1, pending_lanes=SyncLane)) == "sync"
    assert (
        RootScheduler.getRootScheduleMode(SimpleNamespace(tag=1, pending_lanes=InputContinuousLane))
        == "scheduled"
    )
    assert (
        RootScheduler.getRootScheduleMode(SimpleNamespace(tag=1, pending_lanes=DefaultLane))
        == "sync"
    )
    assert (
        RootScheduler.getRootScheduleMode(SimpleNamespace(tag=1, pending_lanes=TransitionLane1))
        == "scheduled"
    )
    assert RootScheduler.getRootScheduleMode(SimpleNamespace(tag=0, pending_lanes=DefaultLane)) == "sync"


def test_root_scheduler_tracks_callback_priority_from_pending_lanes() -> None:
    root = SimpleNamespace(
        tag=1,
        pending_lanes=InputContinuousLane,
        callback_priority=0,
        scheduled_callback_priority=0,
    )

    RootScheduler.ensureRootIsScheduled(root)

    assert root.callback_priority == InputContinuousLane
    assert root.scheduled_callback_priority == InputContinuousLane
    RootScheduler.resetRootSchedule()


def test_root_scheduler_reuses_same_priority_task_without_requeueing_root() -> None:
    RootScheduler.resetRootSchedule()
    root = SimpleNamespace(
        tag=1,
        next=None,
        pending_lanes=InputContinuousLane,
        callback_priority=0,
        scheduled_callback_priority=0,
    )

    RootScheduler.ensureRootIsScheduled(root)
    scheduled_root = RootScheduler.firstScheduledRoot
    original = RootScheduler.scheduleImmediateRootScheduleTask
    scheduled: list[str] = []
    try:
        RootScheduler.scheduleImmediateRootScheduleTask = lambda: scheduled.append("scheduled")
        RootScheduler.didScheduleMicrotask = False
        RootScheduler.ensureRootIsScheduled(root)
    finally:
        RootScheduler.scheduleImmediateRootScheduleTask = original
        RootScheduler.resetRootSchedule()

    assert RootScheduler.firstScheduledRoot is None
    assert scheduled_root is root
    assert scheduled == ["scheduled"]


def test_root_scheduler_updates_callback_priority_when_higher_priority_arrives() -> None:
    RootScheduler.resetRootSchedule()
    root = SimpleNamespace(
        tag=1,
        next=None,
        pending_lanes=InputContinuousLane,
        callback_priority=0,
        scheduled_callback_priority=0,
    )

    RootScheduler.ensureRootIsScheduled(root)
    root.pending_lanes = SyncLane
    RootScheduler.ensureRootIsScheduled(root)

    assert root.callback_priority == SyncLane
    assert root.scheduled_callback_priority == SyncLane
    RootScheduler.resetRootSchedule()


def test_root_scheduler_microtask_rebases_scheduled_priority_before_processing() -> None:
    RootScheduler.resetRootSchedule()
    flushed: list[str] = []

    class FakeReconciler:
        def flush_sync_work(self, container) -> None:
            flushed.append("flush")
            container.pending_lanes = 0

    root = SimpleNamespace(
        tag=1,
        next=None,
        pending_lanes=InputContinuousLane,
        callback_priority=InputContinuousLane,
        scheduled_callback_priority=InputContinuousLane,
        _reconciler=FakeReconciler(),
    )

    RootScheduler.firstScheduledRoot = root
    RootScheduler.lastScheduledRoot = root
    RootScheduler.didScheduleMicrotask = True
    root.pending_lanes = SyncLane

    RootScheduler.processRootScheduleInMicrotask()

    assert flushed == ["flush"]
    assert root.callback_priority == 0
    assert root.scheduled_callback_priority == 0


def test_root_scheduler_builds_root_plan_before_processing() -> None:
    root = SimpleNamespace(
        tag=1,
        pending_lanes=InputContinuousLane,
        callback_priority=0,
        scheduled_callback_priority=0,
    )

    plan = RootScheduler.scheduleTaskForRootDuringMicrotask(root)

    assert plan["root"] is root
    assert plan["next_lanes"] == InputContinuousLane
    assert plan["callback_priority"] == InputContinuousLane
    assert plan["mode"] == "scheduled"
    assert root.callback_priority == InputContinuousLane
    assert root.scheduled_callback_priority == InputContinuousLane


def test_work_loop_passes_selected_lanes_to_reconciler_flush() -> None:
    observed: list[tuple[object, int, int, bool]] = []

    class FakeReconciler:
        def flush_scheduled_updates(
            self,
            container=None,
            priority=None,
            lanes=None,
            *,
            consume_all=True,
        ) -> None:
            observed.append((container, priority, lanes, consume_all))

    root = SimpleNamespace(
        container="container",
        _reconciler=FakeReconciler(),
    )

    performWorkOnRoot(root, InputContinuousLane | DefaultLane)

    assert observed == [("container", InputContinuousLane, InputContinuousLane, False)]


def test_reconciler_tracks_current_render_lanes_during_flush() -> None:
    from pyinkcli.dom import createNode
    from pyinkcli.packages.react_reconciler.ReactFiberReconciler import createReconciler

    root_node = createNode("ink-root")
    reconciler = createReconciler(root_node)
    container = reconciler.create_container(root_node)
    container.element = "element"
    container.pending_render = True
    container.pending_lanes = InputContinuousLane | DefaultLane

    observed: list[tuple[object, int, int]] = []

    def fake_render_tree(_element, _priority):
        observed.append(
            (
                getWorkInProgressRoot(),
                getWorkInProgressRootRenderLanes(),
                container.current_render_lanes,
            )
        )
        return "rendered"

    reconciler._render_tree = fake_render_tree  # type: ignore[method-assign]
    reconciler._attach_rendered_tree = lambda _container: None  # type: ignore[method-assign]
    reconciler._request_host_render = lambda _container, _priority: None  # type: ignore[method-assign]

    reconciler.flush_scheduled_updates(
        container,
        InputContinuousLane,
        lanes=InputContinuousLane,
        consume_all=False,
    )

    assert observed == [(container, InputContinuousLane, InputContinuousLane)]
    assert container.current_render_lanes == 0
    assert getWorkInProgressRoot() is None
    assert getWorkInProgressRootRenderLanes() == 0


def test_reconciler_tracks_commit_and_passive_effect_lanes_during_flush() -> None:
    from pyinkcli.dom import createNode
    from pyinkcli.packages.react_reconciler.ReactFiberReconciler import createReconciler

    root_node = createNode("ink-root")
    reconciler = createReconciler(root_node)
    container = reconciler.create_container(root_node)
    container.element = "element"
    container.pending_render = True
    container.pending_lanes = InputContinuousLane

    observed: list[tuple[bool, object, int]] = []

    reconciler._render_tree = lambda _element, _priority: "rendered"  # type: ignore[method-assign]
    reconciler._request_host_render = lambda _container, _priority: None  # type: ignore[method-assign]

    def fake_attach_rendered_tree(_container) -> None:
        observed.append(
            (
                hasPendingCommitEffects(),
                getRootWithPendingPassiveEffects(),
                getPendingPassiveEffectsLanes(),
            )
        )

    reconciler._attach_rendered_tree = fake_attach_rendered_tree  # type: ignore[method-assign]

    reconciler.flush_scheduled_updates(
        container,
        InputContinuousLane,
        lanes=InputContinuousLane,
        consume_all=False,
    )

    assert observed == [(True, container, InputContinuousLane)]
    assert hasPendingCommitEffects() is False
    assert getRootWithPendingPassiveEffects() is None
    assert getPendingPassiveEffectsLanes() == 0


def test_prepared_commit_carries_explicit_passive_queue_state() -> None:
    from pyinkcli.dom import createNode
    from pyinkcli.packages.react_reconciler.ReactFiberReconciler import createReconciler

    root_node = createNode("ink-root")
    reconciler = createReconciler(root_node)
    container = reconciler.create_container(root_node)
    container.element = "element"
    container.pending_render = True
    container.pending_lanes = InputContinuousLane

    reconciler._render_tree = lambda _element, _priority: "rendered"  # type: ignore[method-assign]
    reconciler._attach_rendered_tree = lambda _container: None  # type: ignore[method-assign]
    reconciler._request_host_render = lambda _container, _priority: None  # type: ignore[method-assign]

    reconciler.flush_scheduled_updates(
        container,
        InputContinuousLane,
        lanes=InputContinuousLane,
        consume_all=False,
    )

    prepared = reconciler._last_prepared_commit
    assert prepared is not None
    assert prepared.passive_effect_state == {
        "deferred_passive_mount_effects": 0,
        "pending_passive_unmount_fibers": 0,
        "has_deferred_passive_work": False,
        "lanes": InputContinuousLane,
    }


def test_flush_pending_effects_drains_deferred_passive_mounts_and_unmounts() -> None:
    from pyinkcli.hooks import _runtime as hooks_runtime

    calls: list[str] = []
    previous_fibers = hooks_runtime._runtime.fibers
    previous_pending_unmounts = hooks_runtime._runtime.pending_passive_unmount_fibers
    hooks_runtime._runtime.fibers = {}
    hooks_runtime._runtime.pending_passive_unmount_fibers = []
    try:
        mount_fiber = hooks_runtime.HookFiber(component_id="mount", element_type="Mount")
        mount_fiber.update_queue = hooks_runtime.FunctionComponentUpdateQueue()
        effect = hooks_runtime.EffectRecord(
            tag=hooks_runtime.HookPassive | hooks_runtime.HookHasEffect,
            create=lambda: calls.append("mount") or None,
            deps=None,
            inst=hooks_runtime.EffectInstance(destroy=None),
        )
        effect.next = effect
        mount_fiber.update_queue.last_effect = effect
        hooks_runtime._runtime.fibers[mount_fiber.component_id] = mount_fiber

        unmount_fiber = hooks_runtime.HookFiber(component_id="unmount", element_type="Unmount")
        unmount_fiber.hook_head = hooks_runtime.HookNode(
            index=0,
            kind="Effect",
            cleanup=lambda: calls.append("unmount"),
        )
        hooks_runtime._runtime.pending_passive_unmount_fibers.append(unmount_fiber)

        flushPendingEffects()

        assert calls == ["unmount", "mount"]
        assert hooks_runtime._get_passive_queue_state()["has_deferred_passive_work"] is False
    finally:
        hooks_runtime._runtime.fibers = previous_fibers
        hooks_runtime._runtime.pending_passive_unmount_fibers = previous_pending_unmounts


def test_flush_sync_work_on_all_roots_skips_non_sync_roots() -> None:
    RootScheduler.resetRootSchedule()
    flushed: list[str] = []

    class FakeReconciler:
        def flush_sync_work(self, container) -> None:
            flushed.append("flush")
            container.pending_lanes = 0

    root = SimpleNamespace(
        tag=1,
        next=None,
        pending_lanes=InputContinuousLane,
        callback_priority=0,
        scheduled_callback_priority=0,
        _reconciler=FakeReconciler(),
    )

    RootScheduler.firstScheduledRoot = root
    RootScheduler.lastScheduledRoot = root

    RootScheduler.flushSyncWorkOnAllRoots()

    assert flushed == []
    assert root.callback_priority == InputContinuousLane
    assert root.scheduled_callback_priority == InputContinuousLane


def test_root_scheduler_keeps_idle_roots_unscheduled_for_now() -> None:
    root = SimpleNamespace(tag=1, pending_lanes=IdleLane)

    assert RootScheduler.shouldScheduleIdleWork(root) is False
    assert RootScheduler.getRootScheduleMode(root) == "idle"


def test_react_hook_effect_tags_export_runtime_flags() -> None:
    assert HasEffect == 1
    assert HookPassiveTag != HookLayoutTag
    assert HookInsertionTag != HookPassiveTag


def test_react_new_context_push_provider_and_read_context() -> None:
    from pyinkcli.packages import react

    context = react.createContext("fallback")
    reconciler = SimpleNamespace(_context_provider_stack=[])

    assert readContext(context) == "fallback"
    pushProvider(reconciler, context, "provided")
    try:
        assert readContext(context) == "provided"
    finally:
        popProvider(reconciler, context)

    assert readContext(context) == "fallback"


def test_react_new_context_records_dependencies_and_detects_changes() -> None:
    from pyinkcli.packages import react

    context = react.createContext("fallback")
    reconciler = SimpleNamespace(_context_provider_stack=[])
    fiber = SimpleNamespace(dependencies=[("stale", "value")])

    prepareToReadContext(fiber)
    try:
        assert readContext(context) == "fallback"
    finally:
        finishReadingContext()

    assert fiber.dependencies == [(context, "fallback")]
    assert checkIfContextChanged(fiber.dependencies) is False

    pushProvider(reconciler, context, "next")
    try:
        assert checkIfContextChanged(fiber.dependencies) is True
    finally:
        popProvider(reconciler, context)


def test_begin_work_delegates_to_reconciler_child_entry() -> None:
    from pyinkcli.component import createElement
    from pyinkcli.dom import createNode
    from pyinkcli.packages.react_reconciler.ReactFiberReconciler import createReconciler

    root = createNode("ink-root")
    reconciler = createReconciler(root)
    result = beginWork(
        reconciler,
        None,
        reconciler._root_fiber,
        createElement("ink-box"),
        root,
        (),
        0,
        "root",
    )

    assert result == 1
    assert root.childNodes[0].nodeName == "ink-box"


def test_concurrent_updates_propagate_child_lanes_to_root() -> None:
    root = SimpleNamespace(tag=3, child_lanes=0, pending_lanes=0)
    parent_alt = SimpleNamespace(child_lanes=0)
    parent = SimpleNamespace(return_fiber=root, child_lanes=0, alternate=parent_alt)
    source_alt = SimpleNamespace(child_lanes=0)
    source = SimpleNamespace(
        return_fiber=parent,
        child_lanes=0,
        lanes=0,
        alternate=source_alt,
    )

    resolved_root = markUpdateLaneFromFiberToRoot(source, None, SyncLane)

    assert resolved_root is root
    assert source.child_lanes == SyncLane
    assert source_alt.child_lanes == SyncLane
    assert parent.child_lanes == SyncLane
    assert parent_alt.child_lanes == SyncLane
    assert root.child_lanes == SyncLane
    assert root.pending_lanes == SyncLane


def test_complete_work_bubbles_child_flags_into_subtree_flags() -> None:
    grandchild = SimpleNamespace(flags=8, subtree_flags=16, sibling=None, lanes=4, child_lanes=32)
    child = SimpleNamespace(flags=2, subtree_flags=4, sibling=grandchild, lanes=2, child_lanes=8)
    parent = SimpleNamespace(child=child, subtree_flags=0, child_lanes=0)

    bubbleProperties(parent)

    assert parent.subtree_flags == 30
    assert parent.child_lanes == 46


def test_complete_work_updates_host_text_and_host_component_memoized_props() -> None:
    text_fiber = SimpleNamespace(
        tag=HostText,
        pending_props={"nodeValue": "hello"},
        memoized_props=None,
        child=None,
        subtree_flags=0,
        flags=0,
    )
    host_fiber = SimpleNamespace(
        tag=HostComponent,
        pending_props={"style": {"flexDirection": "column"}},
        memoized_props=None,
        child=text_fiber,
        subtree_flags=0,
        flags=0,
    )

    completeWork(None, text_fiber)
    completeWork(None, host_fiber)

    assert text_fiber.memoized_props == {"nodeValue": "hello"}
    assert host_fiber.memoized_props == {"style": {"flexDirection": "column"}}


def test_complete_work_updates_class_fragment_and_suspense_memoized_props() -> None:
    class_fiber = SimpleNamespace(
        tag=ClassComponent,
        pending_props={"value": 1},
        memoized_props=None,
        child=None,
        subtree_flags=0,
        flags=0,
    )
    fragment_fiber = SimpleNamespace(
        tag=Fragment,
        pending_props={"children": "x"},
        memoized_props=None,
        child=None,
        subtree_flags=0,
        flags=0,
    )
    suspense_fiber = SimpleNamespace(
        tag=SuspenseComponent,
        pending_props={"fallback": "loading"},
        memoized_props=None,
        child=None,
        subtree_flags=0,
        flags=0,
    )

    completeWork(None, class_fiber)
    completeWork(None, fragment_fiber)
    completeWork(None, suspense_fiber)

    assert class_fiber.memoized_props == {"value": 1}
    assert fragment_fiber.memoized_props == {"children": "x"}
    assert suspense_fiber.memoized_props == {"fallback": "loading"}
    assert suspense_fiber.memoized_state == {"is_suspended": False}


def test_complete_work_inherits_missing_state_node_from_current() -> None:
    current = SimpleNamespace(state_node=object())
    work_in_progress = SimpleNamespace(
        tag=HostComponent,
        state_node=None,
        pending_props={"role": "box"},
        memoized_props=None,
        child=None,
        subtree_flags=0,
        flags=0,
        current_hook=None,
        is_work_in_progress=True,
    )

    completeWork(current, work_in_progress)

    assert work_in_progress.state_node is current.state_node
    assert work_in_progress.memoized_props == {"role": "box"}


def test_complete_work_marks_update_for_changed_host_component_props() -> None:
    current = SimpleNamespace(memoized_props={"role": "old"}, state_node=object())
    work_in_progress = SimpleNamespace(
        tag=HostComponent,
        pending_props={"role": "new"},
        memoized_props={"role": "old"},
        state_node=None,
        child=None,
        subtree_flags=0,
        flags=0,
        current_hook=None,
        is_work_in_progress=True,
    )

    completeWork(current, work_in_progress)

    assert work_in_progress.flags & Update


def test_complete_work_marks_update_for_changed_host_text_props() -> None:
    current = SimpleNamespace(memoized_props={"nodeValue": "old"}, state_node=object())
    work_in_progress = SimpleNamespace(
        tag=HostText,
        pending_props={"nodeValue": "new"},
        memoized_props={"nodeValue": "old"},
        state_node=None,
        child=None,
        subtree_flags=0,
        flags=0,
        current_hook=None,
        is_work_in_progress=True,
    )

    completeWork(current, work_in_progress)

    assert work_in_progress.flags & Update


def test_complete_work_does_not_mark_update_for_mount_or_unchanged_props() -> None:
    mounted = SimpleNamespace(
        tag=HostComponent,
        pending_props={"role": "box"},
        memoized_props=None,
        state_node=None,
        child=None,
        subtree_flags=0,
        flags=0,
        current_hook=None,
        is_work_in_progress=True,
    )
    same_props_current = SimpleNamespace(memoized_props={"role": "same"}, state_node=object())
    same_props_wip = SimpleNamespace(
        tag=HostComponent,
        pending_props={"role": "same"},
        memoized_props={"role": "same"},
        state_node=None,
        child=None,
        subtree_flags=0,
        flags=0,
        current_hook=None,
        is_work_in_progress=True,
    )

    completeWork(None, mounted)
    completeWork(same_props_current, same_props_wip)

    assert mounted.flags == 0
    assert same_props_wip.flags == 0


def test_complete_work_marks_update_for_changed_class_fragment_and_suspense_props() -> None:
    for tag, pending_props in (
        (ClassComponent, {"value": "next"}),
        (Fragment, {"children": "next"}),
        (SuspenseComponent, {"fallback": "next"}),
    ):
        current = SimpleNamespace(memoized_props={"value": "prev"})
        work_in_progress = SimpleNamespace(
            tag=tag,
            pending_props=pending_props,
            memoized_props={"value": "prev"},
            state_node=None,
            child=None,
            subtree_flags=0,
            flags=0,
            current_hook=None,
            is_work_in_progress=True,
        )

        completeWork(current, work_in_progress)

        assert work_in_progress.flags & Update


def test_complete_work_detects_suspense_fallback_subtree_and_root_summary() -> None:
    fallback_child = SimpleNamespace(
        tag=HostText,
        path=("root", "fallback"),
        pending_props={"nodeValue": "loading"},
        memoized_props=None,
        child=None,
        sibling=None,
        subtree_flags=0,
        flags=0,
        state_node=None,
        current_hook=None,
        is_work_in_progress=True,
    )
    suspense = SimpleNamespace(
        tag=SuspenseComponent,
        path=("root",),
        pending_props={"fallback": "loading"},
        memoized_props=None,
        child=fallback_child,
        sibling=None,
        subtree_flags=0,
        flags=0,
        state_node=None,
        current_hook=None,
        is_work_in_progress=True,
    )
    root = SimpleNamespace(
        tag=HostRoot,
        pending_props=None,
        memoized_props=None,
        child=suspense,
        sibling=None,
        subtree_flags=0,
        flags=0,
        state_node=None,
        current_hook=None,
        is_work_in_progress=True,
    )

    completeTree(None, root)

    assert suspense.is_suspended is True
    assert suspense.memoized_state == {"is_suspended": True}
    assert root.contains_suspended_fibers is True
    assert root.memoized_state == {"contains_suspended_fibers": True}


def test_complete_tree_finalizes_nested_child_fibers() -> None:
    child = SimpleNamespace(
        tag=HostText,
        pending_props={"nodeValue": "child"},
        memoized_props=None,
        child=None,
        sibling=None,
        subtree_flags=0,
        flags=0,
        is_work_in_progress=True,
        alternate=None,
    )
    parent = SimpleNamespace(
        tag=HostComponent,
        pending_props={"role": "parent"},
        memoized_props=None,
        child=child,
        sibling=None,
        subtree_flags=0,
        flags=0,
        is_work_in_progress=True,
        alternate=None,
    )

    completeTree(None, parent)

    assert child.memoized_props == {"nodeValue": "child"}
    assert parent.memoized_props == {"role": "parent"}
    assert child.is_work_in_progress is False
    assert parent.is_work_in_progress is False


def test_root_scheduler_marks_microtask_as_scheduled_once() -> None:
    RootScheduler.resetRootSchedule()
    scheduled: list[str] = []
    original = RootScheduler.scheduleImmediateRootScheduleTask
    try:
        RootScheduler.scheduleImmediateRootScheduleTask = lambda: scheduled.append("scheduled")
        RootScheduler.ensureScheduleIsScheduled()
        RootScheduler.ensureScheduleIsScheduled()
        assert RootScheduler.didScheduleMicrotask is True
        assert scheduled == ["scheduled"]
    finally:
        RootScheduler.scheduleImmediateRootScheduleTask = original
        RootScheduler.resetRootSchedule()


def test_root_scheduler_process_microtask_resets_flag_and_flushes() -> None:
    RootScheduler.resetRootSchedule()
    flushed: list[str] = []

    class FakeReconciler:
        def flush_sync_work(self, container) -> None:
            flushed.append("flush")
            container.pending_updates = []
            container.pending_lanes = 0
            container.update_running = False

    container = SimpleNamespace(
        next=None,
        pending_updates=[("update", None)],
        pending_lanes=1,
        update_running=False,
        _reconciler=FakeReconciler(),
    )
    RootScheduler.firstScheduledRoot = container
    RootScheduler.lastScheduledRoot = container
    RootScheduler.didScheduleMicrotask = True

    RootScheduler.processRootScheduleInMicrotask()

    assert flushed == ["flush"]
    assert RootScheduler.didScheduleMicrotask is False
    assert RootScheduler.firstScheduledRoot is None


def test_prepared_commit_carries_root_completion_state() -> None:
    from pyinkcli.component import createElement
    from pyinkcli.dom import createNode
    from pyinkcli.packages.react_reconciler.ReactFiberContainerUpdate import commitContainerUpdate
    from pyinkcli.packages.react_reconciler.ReactFiberReconciler import createReconciler

    root = createNode("ink-root")
    reconciler = createReconciler(root)
    container = reconciler.create_container(root)

    commitContainerUpdate(
        reconciler,
        createElement("ink-box", createElement("ink-text", "hello")),
        container,
    )

    prepared = reconciler._last_prepared_commit
    assert prepared is not None
    assert prepared.root_completion_state is not None
    assert prepared.root_completion_state["tag"] == 3
    assert reconciler._last_root_completion_state == prepared.root_completion_state
    request_render_effect = next(
        effect for effect in prepared.commit_list.layout_effects if effect.tag == "request_render"
    )
    root_completion_effect = next(
        effect for effect in prepared.commit_list.layout_effects if effect.tag == "root_completion_state"
    )
    assert request_render_effect.payload["rootCompletionState"]["tag"] == 3
    assert root_completion_effect.payload["rootCompletionState"]["tag"] == 3


def test_commit_consumes_root_completion_state_for_suspense_summary() -> None:
    from pyinkcli.packages.react_reconciler.ReactFiberCommitWork import (
        CommitList,
        PreparedCommit,
        runPreparedCommitEffects,
    )

    render_requests: list[tuple[int, bool]] = []

    reconciler = SimpleNamespace(
        _last_prepared_commit=None,
        _last_root_completion_state=None,
        _last_root_commit_suspended=None,
        _calculate_layout=lambda _container: None,
        _host_config=SimpleNamespace(
            request_render=lambda priority, immediate: render_requests.append((priority, immediate))
        ),
        _root_fiber=SimpleNamespace(
            deletions=[],
            child=None,
            subtree_flags=0,
            flags=0,
        ),
    )
    container = SimpleNamespace(
        container=SimpleNamespace(
            onComputeLayout=None,
            yogaNode=None,
            isStaticDirty=False,
        ),
        current_update_priority=0,
    )
    prepared = PreparedCommit(
        work_root=object(),
        commit_list=CommitList(
            layout_effects=[
                SimpleNamespace(tag="calculate_layout", payload={}),
                SimpleNamespace(tag="request_render", payload={"immediate": False}),
            ]
        ),
        root_completion_state={"containsSuspendedFibers": True},
    )

    runPreparedCommitEffects(reconciler, container, prepared)

    assert reconciler._last_root_completion_state == {"containsSuspendedFibers": True}
    assert reconciler._last_root_commit_suspended is True
    assert render_requests == [(0, True)]
