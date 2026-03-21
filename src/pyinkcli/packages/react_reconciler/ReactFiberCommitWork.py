"""Commit-phase helpers aligned with ReactFiberCommitWork responsibilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pyinkcli.hooks._runtime import (
    HookHasEffect,
    HookInsertion,
    HookLayout,
    HookPassive,
    EffectRecord,
    _commit_hook_passive_mount_effects,
    _commit_hook_passive_unmount_effects,
    _drain_pending_passive_unmount_fibers,
    _peek_pending_passive_unmount_fibers,
)
from pyinkcli.packages.ink.dom import adoptNodeTree, emitLayoutListeners, removeChildNode
from pyinkcli.packages.react_reconciler.ReactEventPriorities import UpdatePriority
from pyinkcli.packages.react_reconciler.ReactFiberFlags import (
    Callback,
    Deletion,
    Insertion,
    LayoutMask,
    MutationMask,
    Passive,
    PassiveMask,
    Placement,
    Ref,
    Update,
)
from pyinkcli.packages.react_reconciler.ReactWorkTags import (
    ClassComponent,
    FunctionComponent,
    HostComponent,
    HostRoot,
    HostText,
)
from pyinkcli.packages.react_reconciler.ReactFiberClassComponent import captureCommitPhaseError

if TYPE_CHECKING:
    from pyinkcli.packages.react_reconciler.ReactFiberRoot import ReconcilerContainer
    from pyinkcli.packages.react_reconciler.reconciler import _Reconciler


@dataclass
class CommitEffect:
    tag: str
    node_type: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class CommitList:
    mutation_effects: list[CommitEffect] = field(default_factory=list)
    layout_effects: list[CommitEffect] = field(default_factory=list)
    passive_effects: list[CommitEffect] = field(default_factory=list)

    @property
    def effects(self) -> list[CommitEffect]:
        return [
            *self.mutation_effects,
            *self.layout_effects,
            *self.passive_effects,
        ]


@dataclass
class PreparedCommit:
    work_root: Any
    commit_list: CommitList
    callback: Any = None

    @property
    def mutations(self) -> list[dict[str, Any]]:
        return [
            {"op": effect.tag, **({"node": effect.node_type} if effect.node_type else {}), **effect.payload}
            for effect in self.commit_list.effects
        ]


def _assign_ref(ref: Any, value: Any) -> None:
    if ref is None:
        return

    if callable(ref):
        ref(value)
        return

    if isinstance(ref, dict):
        ref["current"] = value
        return

    if hasattr(ref, "current"):
        ref.current = value


def requestHostRender(
    reconciler: _Reconciler,
    priority: UpdatePriority,
    *,
    immediate: bool,
) -> None:
    if reconciler._host_config is not None:
        reconciler._host_config.request_render(priority, immediate)
        return

    if immediate:
        if reconciler._on_immediate_commit is not None:
            reconciler._on_immediate_commit()
        return

    if reconciler._on_commit is not None:
        reconciler._on_commit()


def resetAfterCommit(
    reconciler: _Reconciler,
    container: ReconcilerContainer,
) -> None:
    dom_container = container.container
    if callable(dom_container.onComputeLayout):
        dom_container.onComputeLayout()
    elif dom_container.yogaNode:
        reconciler._calculate_layout(dom_container)

    emitLayoutListeners(dom_container)

    if dom_container.isStaticDirty:
        dom_container.isStaticDirty = False
        requestHostRender(reconciler, container.current_update_priority, immediate=True)
        return

    requestHostRender(reconciler, container.current_update_priority, immediate=False)


def _run_layout_effects(
    reconciler: _Reconciler,
    container: ReconcilerContainer,
    prepared_commit: PreparedCommit,
    *,
    stage: str,
) -> None:
    for effect in prepared_commit.commit_list.layout_effects:
        if stage == "before_fiber_layout" and effect.tag == "calculate_layout":
            dom_container = container.container
            if callable(dom_container.onComputeLayout):
                dom_container.onComputeLayout()
            elif dom_container.yogaNode:
                reconciler._calculate_layout(dom_container)
        elif stage == "after_fiber_layout" and effect.tag == "emit_layout_listeners":
            emitLayoutListeners(container.container)
        elif stage == "after_fiber_layout" and effect.tag == "request_render":
            immediate = bool(effect.payload.get("immediate", False))
            if immediate and container.container.isStaticDirty:
                container.container.isStaticDirty = False
            requestHostRender(
                reconciler,
                container.current_update_priority,
                immediate=immediate,
            )


def _run_passive_effects(
    _reconciler: _Reconciler,
    _container: ReconcilerContainer,
    prepared_commit: PreparedCommit,
) -> None:
    for effect in prepared_commit.commit_list.passive_effects:
        callback = effect.payload.get("callback")
        if callable(callback):
            callback()


def _iter_hook_effects(fiber: Any) -> list[EffectRecord]:
    update_queue = getattr(fiber, "update_queue", None)
    last_effect = getattr(update_queue, "last_effect", None) if update_queue is not None else None
    if last_effect is None:
        return []
    effects: list[EffectRecord] = []
    current = last_effect.next
    while current is not None:
        effects.append(current)
        if current is last_effect:
            break
        current = current.next
    return effects


def _iter_deleted_subtree_fibers(root_fiber: Any) -> list[Any]:
    pending: list[Any] = [root_fiber]
    ordered: list[Any] = []
    seen: set[int] = set()
    while pending:
        fiber = pending.pop()
        fiber_id = id(fiber)
        if fiber_id in seen:
            continue
        seen.add(fiber_id)
        ordered.append(fiber)
        child = getattr(fiber, "child", None)
        siblings: list[Any] = []
        while child is not None:
            siblings.append(child)
            child = getattr(child, "sibling", None)
        pending.extend(reversed(siblings))
    return ordered


def _commitMutationEffectsOnFiber(fiber: Any) -> None:
    _commit_mutation_effect_on_fiber(fiber)


def _commitLayoutEffectOnFiber(reconciler: _Reconciler, fiber: Any) -> None:
    _commit_layout_effect_on_fiber(reconciler, fiber)


def _commitPassiveMountOnFiber(fiber: Any) -> None:
    _commit_passive_effect_on_fiber(fiber)


def _commitHookLayoutEffects(fiber: Any) -> None:
    from pyinkcli.hooks._runtime import _commit_hook_effect_list_mount

    _commit_hook_effect_list_mount(HookLayout | HookHasEffect, fiber)


def _commitHookInsertionEffects(fiber: Any) -> None:
    from pyinkcli.hooks._runtime import _commit_hook_effect_list_mount

    _commit_hook_effect_list_mount(HookInsertion | HookHasEffect, fiber)


def _commitHookUnmountEffectsInDeletedTree(
    deleted_roots: list[Any],
    hook_flags: int,
) -> None:
    from pyinkcli.hooks._runtime import _commit_hook_effect_list_unmount

    seen: set[int] = set()
    for root_fiber in deleted_roots:
        for fiber in _iter_deleted_subtree_fibers(root_fiber):
            fiber_id = id(fiber)
            if fiber_id in seen:
                continue
            seen.add(fiber_id)
            _commit_hook_effect_list_unmount(hook_flags, fiber)


def _attach_ref_for_fiber(fiber: Any) -> None:
    state_node = getattr(fiber, "state_node", None)
    if state_node is None:
        return
    ref = getattr(state_node, "internal_ref", None)
    if ref is None:
        return
    _assign_ref(ref, state_node)


def _detach_ref_from_node(node: Any) -> None:
    ref = getattr(node, "internal_ref", None)
    if ref is None:
        return
    _assign_ref(ref, None)


def _detach_ref_value(ref: Any) -> None:
    _assign_ref(ref, None)


def _detach_deleted_refs(node: Any) -> None:
    _detach_ref_from_node(node)
    for child in getattr(node, "childNodes", []) or []:
        _detach_deleted_refs(child)


def _commit_mutation_effect_on_fiber(fiber: Any) -> None:
    tag = getattr(fiber, "tag", None)
    flags = getattr(fiber, "flags", 0)

    if tag == FunctionComponent and flags & Insertion:
        from pyinkcli.hooks._runtime import _commit_hook_effect_list_unmount

        _commit_hook_effect_list_unmount(HookInsertion | HookHasEffect, fiber)
        _commitHookInsertionEffects(fiber)
        fiber.flags &= ~Insertion

    if tag == FunctionComponent and flags & Callback:
        from pyinkcli.hooks._runtime import _commit_hook_effect_list_unmount

        _commit_hook_effect_list_unmount(HookLayout | HookHasEffect, fiber)

    if tag in (HostComponent, HostText) and flags & Ref:
        for ref in getattr(fiber, "ref_detachments", []):
            _detach_ref_value(ref)
        fiber.ref_detachments = []


def _commit_layout_effect_on_fiber(reconciler: _Reconciler, fiber: Any) -> None:
    tag = getattr(fiber, "tag", None)
    flags = getattr(fiber, "flags", 0)

    if tag == ClassComponent:
        for entry in getattr(fiber, "layout_callbacks", []):
            instance = None
            callback = entry
            if isinstance(entry, tuple) and len(entry) == 2:
                instance, callback = entry
            try:
                callback()
            except Exception as error:
                if instance is not None and captureCommitPhaseError(reconciler, instance, error):
                    continue
                raise
        fiber.layout_callbacks = []
        fiber.flags &= ~Callback
        return

    if tag == FunctionComponent and flags & Callback:
        _commitHookLayoutEffects(fiber)
        fiber.flags &= ~Callback
        return

    if tag in (HostComponent, HostText) and flags & Ref:
        _attach_ref_for_fiber(fiber)
        fiber.flags &= ~Ref
        return

    if tag in (FunctionComponent, HostRoot):
        return


def _commit_passive_effect_on_fiber(fiber: Any) -> None:
    if any((effect.tag & (HookPassive | HookHasEffect)) == (HookPassive | HookHasEffect) for effect in _iter_hook_effects(fiber)):
        _commit_hook_passive_mount_effects(fiber)
    for callback in getattr(fiber, "passive_callbacks", []):
        callback()


def _traverse_mutation_effects(fiber: Any, seen: set[int] | None = None) -> None:
    if seen is None:
        seen = set()
    fiber_id = id(fiber)
    if fiber_id in seen:
        return
    seen.add(fiber_id)
    deletions = getattr(fiber, "deletions", None) or []
    for _deleted in deletions:
        pass
    if getattr(fiber, "flags", 0) & MutationMask:
        _commitMutationEffectsOnFiber(fiber)
    if not (getattr(fiber, "subtree_flags", 0) & MutationMask):
        return
    child = getattr(fiber, "child", None)
    while child is not None:
        if getattr(child, "subtree_flags", 0) & MutationMask or getattr(child, "flags", 0) & MutationMask:
            _traverse_mutation_effects(child, seen)
        child = getattr(child, "sibling", None)


def _traverse_layout_effects(
    reconciler: _Reconciler,
    fiber: Any,
    seen: set[int] | None = None,
) -> None:
    if seen is None:
        seen = set()
    fiber_id = id(fiber)
    if fiber_id in seen:
        return
    seen.add(fiber_id)
    if getattr(fiber, "flags", 0) & LayoutMask:
        _commitLayoutEffectOnFiber(reconciler, fiber)
    if not (getattr(fiber, "subtree_flags", 0) & LayoutMask):
        return
    child = getattr(fiber, "child", None)
    while child is not None:
        if getattr(child, "subtree_flags", 0) & LayoutMask or getattr(child, "flags", 0) & LayoutMask:
            _traverse_layout_effects(reconciler, child, seen)
        child = getattr(child, "sibling", None)


def _traverse_passive_effects(
    fiber: Any,
    seen: set[int] | None = None,
) -> None:
    if seen is None:
        seen = set()
    fiber_id = id(fiber)
    if fiber_id in seen:
        return
    seen.add(fiber_id)
    if getattr(fiber, "flags", 0) & PassiveMask:
        _commitPassiveMountOnFiber(fiber)
    if not (getattr(fiber, "subtree_flags", 0) & PassiveMask):
        return
    child = getattr(fiber, "child", None)
    while child is not None:
        if getattr(child, "subtree_flags", 0) & PassiveMask or getattr(child, "flags", 0) & PassiveMask:
            _traverse_passive_effects(child, seen)
        child = getattr(child, "sibling", None)


def _collect_commit_effects_from_fiber(
    fiber: Any,
    commit_list: CommitList,
    seen: set[int] | None = None,
) -> None:
    if seen is None:
        seen = set()
    fiber_id = id(fiber)
    if fiber_id in seen:
        return
    seen.add(fiber_id)
    deletions = getattr(fiber, "deletions", None) or []
    for deleted in deletions:
        commit_list.mutation_effects.append(
            CommitEffect(
                tag="deletion",
                node_type=getattr(deleted, "nodeName", getattr(fiber, "element_type", None)),
            )
        )

    if getattr(fiber, "subtree_flags", 0):
        child = getattr(fiber, "child", None)
        while child is not None:
            _collect_commit_effects_from_fiber(child, commit_list, seen)
            child = getattr(child, "sibling", None)

    flags = getattr(fiber, "flags", 0)
    element_type = getattr(fiber, "element_type", None)
    if flags & Placement:
        commit_list.mutation_effects.append(
            CommitEffect(tag="placement", node_type=element_type)
        )
    if flags & Update:
        commit_list.mutation_effects.append(
            CommitEffect(tag="update", node_type=element_type)
        )
    if flags & Deletion:
        commit_list.mutation_effects.append(
            CommitEffect(tag="deletion", node_type=element_type)
        )
    hook_effects = _iter_hook_effects(fiber)
    insertion_effects = [
        effect
        for effect in hook_effects
        if (effect.tag & (HookInsertion | HookHasEffect)) == (HookInsertion | HookHasEffect)
    ]
    if insertion_effects or flags & Insertion:
        commit_list.mutation_effects.append(
            CommitEffect(
                tag="hook_insertion",
                node_type=element_type,
                payload={"count": len(insertion_effects)} if insertion_effects else {},
            )
        )
    if flags & Ref:
        if getattr(fiber, "ref_detachments", None):
            commit_list.mutation_effects.append(
                CommitEffect(tag="ref_detach", node_type=element_type)
            )
        commit_list.layout_effects.append(CommitEffect(tag="ref_attach", node_type=element_type))
    layout_effects = [
        effect
        for effect in hook_effects
        if (effect.tag & (HookLayout | HookHasEffect)) == (HookLayout | HookHasEffect)
    ]
    if (
        getattr(fiber, "tag", None) == ClassComponent
        and getattr(fiber, "layout_callbacks", None)
    ):
        commit_list.layout_effects.append(CommitEffect(tag="class_layout", node_type=element_type))
    if layout_effects:
        commit_list.layout_effects.append(
            CommitEffect(
                tag="hook_layout",
                node_type=element_type,
                payload={"count": len(layout_effects)},
            )
        )
    passive_effects = [
        effect
        for effect in hook_effects
        if (effect.tag & (HookPassive | HookHasEffect)) == (HookPassive | HookHasEffect)
    ]
    if passive_effects or flags & Passive:
        commit_list.passive_effects.append(
            CommitEffect(
                tag="passive_mount",
                node_type=element_type,
                payload={"count": len(passive_effects)} if passive_effects else {},
            )
        )


def buildCommitListFromFiberTree(
    root_fiber: Any,
    *,
    is_static_dirty: bool,
) -> CommitList:
    commit_list = CommitList()
    seen_deleted: set[int] = set()
    for fiber in _peek_pending_passive_unmount_fibers():
        for deleted_fiber in _iter_deleted_subtree_fibers(fiber):
            deleted_id = id(deleted_fiber)
            if deleted_id in seen_deleted:
                continue
            seen_deleted.add(deleted_id)
            passive_unmount_effects = [
                effect
                for effect in _iter_hook_effects(deleted_fiber)
                if effect.tag & HookPassive
            ]
            if passive_unmount_effects:
                commit_list.passive_effects.append(
                    CommitEffect(
                        tag="passive_unmount",
                        node_type=getattr(deleted_fiber, "element_type", None),
                        payload={"count": len(passive_unmount_effects)},
                    )
                )
    _collect_commit_effects_from_fiber(root_fiber, commit_list)
    commit_list.layout_effects.extend(
        [
            CommitEffect(tag="calculate_layout"),
            CommitEffect(tag="emit_layout_listeners"),
            CommitEffect(
                tag="request_render",
                payload={"immediate": bool(is_static_dirty)},
            ),
        ]
    )
    return commit_list


def commitPreparedContainer(
    reconciler: _Reconciler,
    container: ReconcilerContainer,
    prepared_commit: PreparedCommit,
) -> None:
    dom_container = container.container
    while dom_container.childNodes:
        child = dom_container.childNodes[0]
        removeChildNode(dom_container, child)
        reconciler._dispose_node(child)

    adoptNodeTree(dom_container, prepared_commit.work_root)
    runPreparedCommitEffects(reconciler, container, prepared_commit)


def runPreparedCommitEffects(
    reconciler: _Reconciler,
    container: ReconcilerContainer,
    prepared_commit: PreparedCommit,
) -> None:
    reconciler._last_prepared_commit = prepared_commit
    deleted_hook_roots = _drain_pending_passive_unmount_fibers()
    deletions = getattr(reconciler._root_fiber, "deletions", None) or []
    for deleted in deletions:
        _detach_deleted_refs(deleted)
    _commitHookUnmountEffectsInDeletedTree(deleted_hook_roots, HookInsertion)
    _traverse_mutation_effects(reconciler._root_fiber)
    _run_layout_effects(
        reconciler,
        container,
        prepared_commit,
        stage="before_fiber_layout",
    )
    _commitHookUnmountEffectsInDeletedTree(deleted_hook_roots, HookLayout)
    _traverse_layout_effects(reconciler, reconciler._root_fiber)
    _run_layout_effects(
        reconciler,
        container,
        prepared_commit,
        stage="after_fiber_layout",
    )
    _commitHookUnmountEffectsInDeletedTree(deleted_hook_roots, HookPassive)
    _traverse_passive_effects(reconciler._root_fiber)
    _run_passive_effects(reconciler, container, prepared_commit)


__all__ = [
    "PreparedCommit",
    "CommitList",
    "CommitEffect",
    "buildCommitListFromFiberTree",
    "runPreparedCommitEffects",
    "requestHostRender",
    "resetAfterCommit",
]
